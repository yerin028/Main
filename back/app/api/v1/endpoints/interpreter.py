import base64
import json
import random
import re
from datetime import datetime, timezone
import concurrent.futures
import os
from dotenv import load_dotenv

import cv2
import numpy as np
import mediapipe as mp
from openai import AzureOpenAI
from fastapi import APIRouter, HTTPException, status, Request
from pymongo.errors import PyMongoError

from app.core.mongo_database import get_interpreter_collection, db
from app.schemas.interpreter import TranslateRequestSchema, TranslateResponseSchema

# APIRouter는 기능별 API 주소를 묶는 FastAPI 도구입니다.
# 이 파일에서는 /interpreter 아래에 들어갈 수어통역 API들을 정의합니다.
router = APIRouter()

# .env 파일 로드
load_dotenv()

# 백엔드 루트 및 디버깅 파일 경로 동적 생성
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACK_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "..", ".."))
DEBUG_LOG_PATH = os.path.join(BACK_DIR, "interpreter_debug.log")
DEBUG_CAPTURE_PATH = os.path.join(BACK_DIR, "debug_capture.jpg")

# 환경 변수에서 값 가져오기
azure_client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_VERSION")
)

# 디플로이먼트 네임도 환경 변수로 관리하면 편해
DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4-04-14-2")

# 미디어파이프 Hands & Pose 초기화 (동적 신체 랜드마크 비교용)
mp_hands = mp.solutions.hands
hands_detector = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.5)
mp_pose = mp.solutions.pose
pose_detector = mp_pose.Pose(min_detection_confidence=0.5)

# 사용자별(IP 기반) 최근 손 랜드마크 궤적 히스토리 저장소 (동적 action 판별용)
landmarks_history = {}
MAX_HISTORY_LEN = 8

# 로컬 수어 규칙 검증기: 번역 단어의 요구 동작(양손 여부, 수형, 액션)과 실제 사용자의 동작이 일치하는지 MongoDB Parsed_Rules 대조 검증
def validate_sign_rules(word_name: str, payload: list) -> bool:
    debug_log_path = DEBUG_LOG_PATH
    try:
        rule_doc = db['Parsed_Rules'].find_one({"word_name": word_name})
        if not rule_doc:
            msg = f"No rule document found in Parsed_Rules for word: {word_name}. Bypassing validation."
            try:
                with open(debug_log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now()}] [VALIDATOR] {msg}\n")
            except Exception: pass
            return True
            
        sequence = rule_doc.get("sequence", [])
        if not sequence or len(payload) == 0:
            return True
            
        rule_step = sequence[0]
        user_step = payload[0]
        
        r_rule = rule_step.get("right_hand", {})
        l_rule = rule_step.get("left_hand", {})
        
        if isinstance(r_rule, str):
            try: r_rule = json.loads(r_rule)
            except: r_rule = {}
        if isinstance(l_rule, str):
            try: l_rule = json.loads(l_rule)
            except: l_rule = {}
            
        r_user = user_step.get("right_hand", {})
        l_user = user_step.get("left_hand", {})
        
        rule_uses_right = r_rule.get("shape", "none") != "none"
        rule_uses_left = l_rule.get("shape", "none") != "none"
        
        user_uses_right = r_user.get("shape", "none") != "none"
        user_uses_left = l_user.get("shape", "none") != "none"
        
        # 1. 한손 vs 양손 일치 여부 검증
        if rule_uses_right != user_uses_right or rule_uses_left != user_uses_left:
            msg = f"One-hand vs Two-hand mismatch for {word_name}. Rule uses R:{rule_uses_right} L:{rule_uses_left}, User uses R:{user_uses_right} L:{user_uses_left}"
            try:
                with open(debug_log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now()}] [VALIDATOR] {msg}\n")
            except Exception: pass
            return False
            
        # 2. 수형 일치 여부 검증
        def is_shape_compatible(rule_shape, user_shape):
            if not rule_shape or rule_shape == "none":
                return not user_shape or user_shape == "none"
            if not user_shape or user_shape == "none":
                return False
            rule_shape = str(rule_shape).lower().strip()
            user_shape = str(user_shape).lower().strip()
            
            if rule_shape in ["fist", "주먹"] and user_shape in ["fist", "주먹"]:
                return True
            if rule_shape in ["open_palm", "편 손", "5지"] and user_shape in ["open_palm", "편 손", "5지"]:
                return True
            return rule_shape == user_shape or rule_shape in user_shape or user_shape in rule_shape

        if rule_uses_right:
            if not is_shape_compatible(r_rule.get("shape", ""), r_user.get("shape", "")):
                msg = f"Right hand shape mismatch for {word_name}. Rule: {r_rule.get('shape')}, User: {r_user.get('shape')}"
                try:
                    with open(debug_log_path, "a", encoding="utf-8") as f:
                        f.write(f"[{datetime.now()}] [VALIDATOR] {msg}\n")
                except Exception: pass
                return False
        if rule_uses_left:
            if not is_shape_compatible(l_rule.get("shape", ""), l_user.get("shape", "")):
                msg = f"Left hand shape mismatch for {word_name}. Rule: {l_rule.get('shape')}, User: {l_user.get('shape')}"
                try:
                    with open(debug_log_path, "a", encoding="utf-8") as f:
                        f.write(f"[{datetime.now()}] [VALIDATOR] {msg}\n")
                except Exception: pass
                return False
                
        # 3. 액션(동적 움직임) 일치 여부 검증
        rule_act = rule_step.get("action", "none")
        user_act = user_step.get("action", "none")
        if rule_act != "none" and user_act == "none":
            msg = f"Action mismatch for {word_name}. Rule action: {rule_act}, User action: {user_act}"
            try:
                with open(debug_log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now()}] [VALIDATOR] {msg}\n")
            except Exception: pass
            return False
            
        msg = f"Validation successful for {word_name}!"
        try:
            with open(debug_log_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] [VALIDATOR] {msg}\n")
        except Exception: pass
        return True
    except Exception as e:
        msg = f"Local validator exception for {word_name}: {e}"
        try:
            with open(debug_log_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] [VALIDATOR] {msg}\n")
        except Exception: pass
        return True

# 정제된 텍스트가 수어 단어가 아닌 수형/포지션/액션 템플릿 변수명인지 검증하는 헬퍼 함수
def is_invalid_sign_word(word: str) -> bool:
    word = word.strip()
    # 1. 2지, 1·2지 등 수형 명칭 제거
    if re.match(r"^[0-9·,]+지$", word):
        return True
        
    # 2. 서브스트링(포함 여부) 블랙리스트 - 발견 즉시 차단
    substring_blacklists = [
        "기준", "실시간", "웹캠", "감지", "명세", "규칙", "category", 
        "step", "description", "steps", "parameters", "right_hand", 
        "left_hand", "action", "touching"
    ]
    if any(k in word.lower() for k in substring_blacklists):
        return True
        
    # 3. 단독 일치(exact match) 블랙리스트 - 신체 부위 및 상태 변수 한글 단독 오노출 차단
    exact_blacklists = [
        "배", "배꼽", "가슴", "얼굴", "코", "뺨", "손", "주먹", "편 손",
        "none", "fist", "face", "chest", "belly", "contact", "near", 
        "upward", "downward", "shake", "leftward", "rightward", "up_down",
        "오른손", "왼손", "동작"
    ]
    if word.lower() in exact_blacklists:
        return True
        
    return False


# AI 응답에서 잡다한 템플릿 설명을 제외하고 매칭된 수어 단어만 정교하게 추출하는 정제 함수
def clean_ai_reply(reply: str) -> str:
    reply = reply.strip()
    
    # 1. 만약 전체가 JSON 형식인 경우 파싱하여 내부에서 실제 단어 정보 추출 시도
    if reply.startswith("{") and reply.endswith("}"):
        try:
            data = json.loads(reply)
            # 학습 데이터 상 수어 단어 명칭이 들어가는 유효한 키들 검사
            for key in ["word_name", "word", "title"]:
                if key in data and data[key]:
                    val = data[key].strip()
                    if not is_invalid_sign_word(val):
                        return val
            # steps 내부 검사
            if "steps" in data and isinstance(data["steps"], list) and len(data["steps"]) > 0:
                step = data["steps"][0]
                for key in ["word_name", "word"]:
                    if key in step and step[key]:
                        val = step[key].strip()
                        if not is_invalid_sign_word(val):
                            return val
        except Exception:
            pass

    # 2. 작은 따옴표나 큰 따옴표로 감싸진 단어 파싱 ('서양' -> 서양)
    match_quotes = re.search(r"['\"]([^'\"]+)['\"]", reply)
    if match_quotes:
        val = match_quotes.group(1).strip()
        if not is_invalid_sign_word(val):
            return val

    # 3. '단어: 서양' 또는 '단어 : 서양' 과 같은 구조 파싱
    match_colon = re.search(r"(?:단어|결과)\s*:\s*([^\n\r]+)", reply)
    if match_colon:
        val = match_colon.group(1).strip()
        val = re.sub(r"['\"]", "", val).strip()
        if not is_invalid_sign_word(val):
            return val

    # 4. 문장형 표현 파싱 (예: "해당 행동 패턴은 '서양'을 의미합니다.")
    match_meaning = re.search(r"([가-힣a-zA-Z0-9\s]+)을\s+의미합니다", reply)
    if match_meaning:
        val = match_meaning.group(1).strip()
        val = re.sub(r"['\"]", "", val).strip()
        if not is_invalid_sign_word(val):
            return val

    # 5. 최종 필터링 및 블랙리스트 단어 검증
    if is_invalid_sign_word(reply):
        return "동작 감지 대기 중... (카메라 앞에 손을 보여주세요)"

    # 정제된 텍스트의 길이가 너무 길면 (예: 10자 초과 문장) 수어 단어가 아니므로 거름
    if len(reply) > 10:
        return "동작 감지 대기 중... (카메라 앞에 손을 보여주세요)"

    return reply


# OpenAI 호출을 재사용하기 위해 분리한 헬퍼 함수
def call_openai_model(payload: list, category: str) -> str:
    try:
        # 학습 시 사용한 system prompt와 동일하게 system role 메시지 추가
        system_content = f"너는 [{category}] 카테고리에 속한 수어 동작을 판별하는 전문가 AI이다. 입력받은 단계별 수형(right_hand, left_hand), 위치(position), 움직임(action) JSON 규칙을 분석하여 이와 일치하는 한국어 수어 단어명 하나만 정확히 리턴해라."
        response = azure_client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": system_content
                },
                {
                    "role": "user", 
                    "content": f"카테고리: {category} | 행동 명세 데이터: {json.dumps(payload, ensure_ascii=False)}"
                }
            ],
            max_tokens=50,
            temperature=0.0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Azure OpenAI Error during model call: {e}")
        return ""


def generate_behavior_description(payload: list) -> str:
    if not payload or len(payload) == 0:
        return "동작 감지 대기 중..."
    
    data = payload[0]
    r = data.get("right_hand", {})
    l = data.get("left_hand", {})
    act = data.get("action", "none")
    
    r_shape = r.get("shape", "none")
    r_pos = r.get("position", "none")
    r_touch = r.get("touching", "none")
    
    l_shape = l.get("shape", "none")
    l_pos = l.get("position", "none")
    l_touch = l.get("touching", "none")
    
    parts = []
    
    # 오른손 매핑
    if r_shape != "none":
        r_part = "오른손"
        shape_map = {
            "주먹": "주먹을 쥔 채",
            "fist": "주먹을 쥔 채",
            "편 손": "손가락을 모두 편 채",
            "open_palm": "손가락을 모두 편 채",
            "1지": "엄지(1지)만 편 채",
            "2지": "검지(2지)만 편 채",
            "3지": "중지(3지)만 편 채",
            "4지": "약지(4지)만 편 채",
            "5지": "새끼(5지)만 편 채",
        }
        r_shape_ko = shape_map.get(r_shape, f"'{r_shape}' 모양으로")
        r_part += f" {r_shape_ko}"
        
        pos_map = {"face": "얼굴", "cheek": "뺨", "chest": "가슴", "belly": "배(배꼽)"}
        touch_map = {"contact": "에 접촉하고", "near": " 근처로 가져가고"}
        
        r_pos_ko = pos_map.get(r_pos, "")
        r_touch_ko = touch_map.get(r_touch, "")
        
        if r_pos_ko:
            if r_touch_ko:
                r_part += f" {r_pos_ko}{r_touch_ko}"
            else:
                r_part += f" {r_pos_ko} 위치에 두고"
        else:
            r_part += " 위치를 유지하며"
            
        parts.append(r_part)

    # 왼손 매핑
    if l_shape != "none":
        l_part = "왼손"
        shape_map = {
            "주먹": "주먹을 쥔 채",
            "fist": "주먹을 쥔 채",
            "편 손": "손가락을 모두 편 채",
            "open_palm": "손가락을 모두 편 채",
            "1지": "엄지(1지)만 편 채",
            "2지": "검지(2지)만 편 채",
            "3지": "중지(3지)만 편 채",
            "4지": "약지(4지)만 편 채",
            "5지": "새끼(5지)만 편 채",
        }
        l_shape_ko = shape_map.get(l_shape, f"'{l_shape}' 모양으로")
        l_part += f" {l_shape_ko}"
        
        pos_map = {"face": "얼굴", "cheek": "뺨", "chest": "가슴", "belly": "배(배꼽)"}
        touch_map = {"contact": "에 접촉하고", "near": " 근처로 가져가고"}
        
        l_pos_ko = pos_map.get(l_pos, "")
        l_touch_ko = touch_map.get(l_touch, "")
        
        if l_pos_ko:
            if l_touch_ko:
                l_part += f" {l_pos_ko}{l_touch_ko}"
            else:
                l_part += f" {l_pos_ko} 위치에 두고"
        else:
            l_part += " 위치를 유지하며"
            
        parts.append(l_part)
        
    if not parts:
        return "동작 감지 대기 중... (카메라 앞에 손을 보여주세요)"
        
    sentence = ", ".join(parts)
    
    # 동적 액션 해석
    act_map = {
        "upward": "위로 쓸어올리는 동작을 함",
        "downward": "아래로 쓸어내리는 동작을 함",
        "shake": "흔드는 동작을 함",
        "up_down": "위아래로 흔드는 동작을 함",
        "leftward": "왼쪽으로 이동하는 동작을 함",
        "rightward": "오른쪽으로 이동하는 동작을 함",
    }
    act_ko = act_map.get(act, "")
    
    if act_ko:
        sentence += f" + {act_ko}"
    else:
        sentence += " + 상태를 유지함"
        
    return sentence


# 이미지 데이터를 입력받아 MediaPipe 랜드마크 분석 및 Azure OpenAI 추론을 통해 수어 문장을 인식합니다.
def predict_sign_language_to_korean(image_data: str, category: str = "개념", client_ip: str = "default") -> tuple[str, float]:
    # 프론트에서 canvas.toDataURL()로 보낸 값은 data:image/jpeg;base64,... 형태입니다.
    if not image_data.startswith("data:image/"):
        raise ValueError("image_data must be a base64 data URL.")

    # base64 이미지 디코딩
    try:
        header, encoded = image_data.split(",", 1)
        image_bytes = base64.b64decode(encoded)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Decoded image is empty.")
        # 디버깅을 위해 프론트로부터 수신한 이미지 디스크 저장
        cv2.imwrite(DEBUG_CAPTURE_PATH, img)
    except Exception as e:
        raise ValueError(f"Failed to decode base64 image: {str(e)}")

    # 미디어파이프 처리를 위해 RGB 변환 및 Hands/Pose 처리
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    hand_results = hands_detector.process(img_rgb)
    pose_results = pose_detector.process(img_rgb)

    # 신체 랜드마크 기준 x, y좌표 초기값 (포즈 미검출 시 절대 좌표 백업)
    nose_x = 0.5
    nose_y = 0.3
    shoulder_y = 0.55
    hip_y = 0.8

    if pose_results.pose_landmarks:
        p_lms = pose_results.pose_landmarks.landmark
        nose_x = p_lms[0].x
        nose_y = p_lms[0].y
        shoulder_y = (p_lms[11].y + p_lms[12].y) / 2.0
        hip_y = (p_lms[23].y + p_lms[24].y) / 2.0

    r_shape, r_pos, r_touch = "none", "none", "none"
    l_shape, l_pos, l_touch = "none", "none", "none"
    action_type = "none"

    # 사용자 IP별 히스토리 객체 초기화 및 갱신
    if client_ip not in landmarks_history:
        landmarks_history[client_ip] = []
        
    current_frame_landmarks = {"right": None, "left": None}

    # 디버깅용 텍스트 파일 경로
    debug_log_path = DEBUG_LOG_PATH

    if hand_results.multi_hand_landmarks and hand_results.multi_handedness:
        for idx, hand_handedness in enumerate(hand_results.multi_handedness):
            label = hand_handedness.classification[0].label # Left 또는 Right
            landmarks = hand_results.multi_hand_landmarks[idx].landmark
            coords = [(lm.x, lm.y) for lm in landmarks]
            
            if label == "Right":
                current_frame_landmarks["right"] = coords
            else:
                current_frame_landmarks["left"] = coords

            # A) 손가락 펴짐 여부 판별 및 수형(Shape) 조합 알고리즘
            # 3D hand scale (손목 0번에서 중지 관절 9번까지의 3D 거리)
            dx = landmarks[0].x - landmarks[9].x
            dy = landmarks[0].y - landmarks[9].y
            dz = landmarks[0].z - landmarks[9].z
            hand_scale = (dx*dx + dy*dy + dz*dz)**0.5
            if hand_scale == 0:
                hand_scale = 0.001

            # 엄지 끝 4번과 중지 관절 9번 사이의 3D 거리 측정
            tdx = landmarks[4].x - landmarks[9].x
            tdy = landmarks[4].y - landmarks[9].y
            tdz = landmarks[4].z - landmarks[9].z
            thumb_to_mid = (tdx*tdx + tdy*tdy + tdz*tdz)**0.5
            
            # 손가락 2~5지의 펴짐 여부를 손목(0번) 기준 3D 정규화 유클리드 비로 판정 (앵글/원근 왜곡 제거)
            def is_finger_open(tip_idx, base_idx):
                base_dx = landmarks[base_idx].x - landmarks[0].x
                base_dy = landmarks[base_idx].y - landmarks[0].y
                base_dz = landmarks[base_idx].z - landmarks[0].z
                base_dist = (base_dx*base_dx + base_dy*base_dy + base_dz*base_dz)**0.5
                if base_dist == 0:
                    base_dist = 0.001
                tip_dx = landmarks[tip_idx].x - landmarks[0].x
                tip_dy = landmarks[tip_idx].y - landmarks[0].y
                tip_dz = landmarks[tip_idx].z - landmarks[0].z
                tip_dist = (tip_dx*tip_dx + tip_dy*tip_dy + tip_dz*tip_dz)**0.5
                return (tip_dist / base_dist) > 1.25

            is_1_open = (thumb_to_mid / hand_scale) > 0.6
            is_2_open = is_finger_open(8, 5)
            is_3_open = is_finger_open(12, 9)
            is_4_open = is_finger_open(16, 13)
            is_5_open = is_finger_open(20, 17)

            opened_fingers = []
            if is_1_open: opened_fingers.append("1")
            if is_2_open: opened_fingers.append("2")
            if is_3_open: opened_fingers.append("3")
            if is_4_open: opened_fingers.append("4")
            if is_5_open: opened_fingers.append("5")

            # 학습 데이터셋 형식에 맞춰 shapes와 positions 변환
            if len(opened_fingers) == 0:
                shape_str = "fist"
            elif len(opened_fingers) >= 4:
                shape_str = "open_palm"
            else:
                shape_str = ", ".join([f"{f}지" for f in opened_fingers])
            
            # B) 손의 상대적 위치 계산 (신체 상대 좌표 기준 - 어깨선과 어깨/골반 중간선 적용)
            avg_x = sum([lm.x for lm in landmarks]) / 21
            avg_y = sum([lm.y for lm in landmarks]) / 21
            chest_hip_mid = (shoulder_y + hip_y) / 2.0
            
            if avg_y < shoulder_y - 0.02: # 어깨선보다 위쪽이면 face
                pos_str = "face"
            elif avg_y < chest_hip_mid:
                pos_str = "chest"
            else:
                pos_str = "none"  # 학습 데이터셋의 하단 기본값은 none입니다.
            
            # C) 접촉(touching) 판정 로직
            touch_str = "none"
            if pos_str == "face":
                dist_to_nose = ((avg_x - nose_x)**2 + (avg_y - nose_y)**2)**0.5
                if dist_to_nose < 0.16:
                    touch_str = "contact"
                elif dist_to_nose < 0.28:
                    touch_str = "near"
            
            # 디버깅 로그 기록
            try:
                with open(debug_log_path, "a", encoding="utf-8") as f:
                    f.write(f"MP Label: {label} | avg_y: {avg_y:.4f} | Nose_Y: {nose_y:.4f} | Sh_Y: {shoulder_y:.4f} | Hip_Y: {hip_y:.4f} | Pos: {pos_str} | Shape: {shape_str} | Touch: {touch_str}\n")
            except Exception:
                pass

            # 좌/우 매칭 (사용자의 실제 오른손이 Left로 오인되는 라벨 매칭 스왑 적용)
            # MediaPipe label "Left" ➡️ 실질적으로 오른손(Right) 필드에 대입
            if label == "Left":
                r_shape = shape_str
                r_pos = pos_str
                r_touch = touch_str
            else:
                l_shape = shape_str
                l_pos = pos_str
                l_touch = touch_str

    # 히스토리 큐에 추가 및 최대 크기 유지
    landmarks_history[client_ip].append(current_frame_landmarks)
    if len(landmarks_history[client_ip]) > MAX_HISTORY_LEN:
        landmarks_history[client_ip].pop(0)

    # D) 프레임 간 좌표값 변화를 이용한 동적 action 판정
    history = landmarks_history[client_ip]
    r_coords = [h["right"][0] for h in history if h["right"] is not None]  # 0번 손목 기준
    l_coords = [h["left"][0] for h in history if h["left"] is not None]

    def analyze_coords_to_action(coords, threshold=0.03) -> str:
        if len(coords) < 3:
            return "none"
        
        # 1) 미세 진동(jitter) 제거를 위해 인접 프레임 간 차이가 0.008 이상인 움직임만 수형 방향 판별에 사용
        valid_diffs_x = []
        valid_diffs_y = []
        for i in range(1, len(coords)):
            dx_i = coords[i][0] - coords[i-1][0]
            dy_i = coords[i][1] - coords[i-1][1]
            if abs(dx_i) > 0.008:
                valid_diffs_x.append(dx_i)
            if abs(dy_i) > 0.008:
                valid_diffs_y.append(dy_i)
        
        # 2) 노이즈 필터링된 유효 동작 간의 부호 바뀜(방향 전환) 카운트
        x_changes = 0
        for i in range(1, len(valid_diffs_x)):
            if valid_diffs_x[i] * valid_diffs_x[i-1] < 0:
                x_changes += 1
                
        y_changes = 0
        for i in range(1, len(valid_diffs_y)):
            if valid_diffs_y[i] * valid_diffs_y[i-1] < 0:
                y_changes += 1
        
        if x_changes >= 2:
            return "shake"
        if y_changes >= 2:
            return "up_down"
            
        # 3) 단방향 큰 이동 판정
        total_dx = coords[-1][0] - coords[0][0]
        total_dy = coords[-1][1] - coords[0][1]
        
        if abs(total_dy) > abs(total_dx) and abs(total_dy) > threshold:
            return "upward" if total_dy < 0 else "downward"
        elif abs(total_dx) > abs(total_dy) and abs(total_dx) > threshold:
            return "rightward" if total_dx > 0 else "leftward"
            
        return "none"

    if r_shape != "none":
        action_type = analyze_coords_to_action(r_coords, threshold=0.03)
    elif l_shape != "none":
        action_type = analyze_coords_to_action(l_coords, threshold=0.03)

    # client.py의 규격 매칭을 위한 행동 명세 페이로드 구성
    live_action_payload = [
        {
            "step": 1,
            "right_hand": {"shape": r_shape, "position": r_pos, "touching": r_touch},
            "left_hand": {"shape": l_shape, "position": l_pos, "touching": l_touch},
            "action": action_type
        }
    ]

    print(f"DEBUG INPUT - Category: {category} | Payload: {json.dumps(live_action_payload, ensure_ascii=False)}")
    
    # 손이 감지되지 않았을 때 AI 모델 호출 없이 빠른 대기 상태 응답 반환
    if r_shape == "none" and l_shape == "none":
        return "동작 감지 대기 중... (카메라 앞에 손을 보여주세요)", 0.0

    try:
        with open(debug_log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- [시작] Category: {category} ---\n")
            f.write(f"Detected Shape: 우={r_shape}({r_pos},{r_touch}) | 좌={l_shape}({l_pos},{l_touch}) | 액션={action_type}\n")
    except Exception:
        pass

    # 병렬 다중 매칭 후보 페이로드 구성 (학습 포맷에 맞춰 description 추가 및 노이즈 보정 후보 구성)
    candidates = []
    
    # 0. 원본 페이로드 (with auto-generated description)
    p_original = [
        {
            "step": 1,
            "right_hand": live_action_payload[0]["right_hand"].copy(),
            "left_hand": live_action_payload[0]["left_hand"].copy(),
            "action": action_type
        }
    ]
    p_original[0]["description"] = generate_behavior_description(p_original)
    candidates.append(("original", p_original))
    
    # 오른손 또는 왼손 중 하나라도 감지된 경우에만 보정 시작
    r_f = live_action_payload[0]["right_hand"].copy()
    l_f = live_action_payload[0]["left_hand"].copy()
    act = action_type

    # 1) 접촉 노이즈 보정 후보 (contact <-> near 교차 대입)
    r_f_alt = r_f.copy()
    l_f_alt = l_f.copy()
    touch_modified = False

    if r_f_alt["touching"] == "contact":
        r_f_alt["touching"] = "near"
        touch_modified = True
    elif r_f_alt["touching"] == "near":
        r_f_alt["touching"] = "contact"
        touch_modified = True

    if l_f_alt["touching"] == "contact":
        l_f_alt["touching"] = "near"
        touch_modified = True
    elif l_f_alt["touching"] == "near":
        l_f_alt["touching"] = "contact"
        touch_modified = True

    if touch_modified:
        p_touch = [
            {"step": 1, "right_hand": r_f_alt, "left_hand": l_f_alt, "action": act}
        ]
        p_touch[0]["description"] = generate_behavior_description(p_touch)
        candidates.append(("touch_alt", p_touch))

    # 2) 액션 움직임 노이즈 보정 후보 (움직임 감지되었을 때 정지 상태 "none"로도 매칭)
    if act != "none":
        p_action = [
            {
                "step": 1,
                "right_hand": r_f.copy(),
                "left_hand": l_f.copy(),
                "action": "none"
            }
        ]
        p_action[0]["description"] = generate_behavior_description(p_action)
        candidates.append(("action_alt", p_action))

    # 중복 제거
    unique_candidates = []
    seen = set()
    for name, p in candidates:
        serialized = json.dumps(p, sort_keys=True)
        if serialized not in seen:
            seen.add(serialized)
            unique_candidates.append((name, p))

    # 병렬 쿼리 수행
    results = [None] * len(unique_candidates)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_to_index = {
            executor.submit(call_openai_model, p, category): idx
            for idx, (name, p) in enumerate(unique_candidates)
        }
        for future in concurrent.futures.as_completed(future_to_index):
            idx = future_to_index[future]
            name, p = unique_candidates[idx]
            try:
                raw_reply = future.result()
                cleaned = clean_ai_reply(raw_reply)
                results[idx] = (name, p, raw_reply, cleaned)
            except Exception as e:
                results[idx] = (name, p, "", f"Error: {e}")

    # 카테고리 기반 화이트리스트 단어 목록 조회 (학습 데이터셋 외 단어 환각 필터링)
    allowed_words = []
    try:
        from app.core.mongo_database import get_dictionary_collection
        collection = get_dictionary_collection()
        category_sources = [category]
        if category == "개념":
            category_sources = ["개념", "자연"]
        elif category == "생활":
            category_sources = ["경제생활", "식생활", "의생활", "주생활", "의학", "교통", "나라명 및 지명"]
        elif category == "의료":
            category_sources = ["의학", "의료"]

        docs = collection.find({"category_name": {"$in": category_sources}})
        for doc in docs:
            w_name = doc.get("word_name")
            if w_name:
                allowed_words.append(w_name.strip())
    except Exception as e:
        print(f"Failed to fetch whitelist from MongoDB: {e}")

    # 최종 매칭 선택 (우선순위 순으로 유효한 한국어 단어 판별 & 카테고리 화이트리스트 필터링)
    final_cleaned = None
    final_raw = None
    selected_name = None
    selected_payload = None

    for name, p, raw, cleaned in results:
        if cleaned and "동작 감지 대기 중" not in cleaned:
            # 화이트리스트 체크
            is_allowed = False
            if not allowed_words:  # 예외 상황 시 전체 허용 백업
                is_allowed = True
            else:
                for allowed in allowed_words:
                    if cleaned in allowed or allowed in cleaned:
                        cleaned = allowed
                        is_allowed = True
                        break
            
            if is_allowed:
                # 로컬 수어 규칙 검증기를 통한 정밀 필터링 추가
                if validate_sign_rules(cleaned, p):
                    final_cleaned = cleaned
                    final_raw = raw
                    selected_name = name
                    selected_payload = p
                    break
                else:
                    try:
                        with open(debug_log_path, "a", encoding="utf-8") as f:
                            f.write(f"[{datetime.now()}] Mismatch candidate '{cleaned}' filtered out by validate_sign_rules.\n")
                    except Exception:
                        pass

    # 로깅 및 리턴
    try:
        with open(debug_log_path, "a", encoding="utf-8") as f:
            f.write(f"--- 병렬 다중 매칭 결과 ({len(results)}개 후보) ---\n")
            for name, p, raw, cleaned in results:
                f.write(f"[{name}] Payload: {json.dumps(p, ensure_ascii=False)} | Raw: {raw} | Cleaned: {cleaned}\n")
            f.write(f"==> Selected: [{selected_name}] Cleaned={final_cleaned}\n\n")
    except Exception:
        pass

    if final_cleaned:
        return final_cleaned, 0.95
    else:
        return "동작 감지 대기 중... (카메라 앞에 손을 보여주세요)", 0.0


translation_cache = {}

# 한국어 인식 결과를 영어로 바꾸는 함수입니다.
# 딕셔너리에 없으면 Azure OpenAI를 이용하여 번역합니다.
def translate_korean_to_english(korean_text: str) -> str:
    korean_text = korean_text.strip()
    if korean_text in translation_cache:
        return translation_cache[korean_text]

    translations = {
        "안녕하세요": "Hello.",
        "만나서 반갑습니다": "Nice to meet you.",
        "감사합니다": "Thank you.",
        "도움이 필요합니다": "I need help.",
        "동작 감지 대기 중... (카메라 앞에 손을 보여주세요)": "Waiting for motion detection... (Please show your hand in front of the camera)",
    }
    if korean_text in translations:
        return translations[korean_text]
        
    try:
        response = azure_client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional translator. Translate the given Korean description of hand gestures/motions to English. Output only the translation, nothing else."
                },
                {
                    "role": "user",
                    "content": korean_text
                }
            ],
            max_tokens=25,
            temperature=0.0
        )
        english_translation = response.choices[0].message.content.strip()
        translation_cache[korean_text] = english_translation
        return english_translation
    except Exception as e:
        print(f"Translation dynamic error: {e}")
        return korean_text


# 요구사항명세서의 POST /api/v1/interpreter/translate에 해당하는 엔드포인트입니다.
# main.py에서 /api/v1 prefix가 붙고, api.py에서 /interpreter prefix가 붙기 때문에
# 최종 주소는 /api/v1/interpreter/translate가 됩니다.
@router.post(
    "/translate",
    response_model=TranslateResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def translate_sign_language(
    payload: TranslateRequestSchema,
    request: Request,
):
    # image_data가 비어 있으면 수어 인식을 할 수 없으므로 400 Bad Request를 반환합니다.
    if not payload.image_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="image_data 값이 필요합니다.",
        )

    try:
        # 1단계: 카메라 이미지에서 수어를 인식해 한국어 문장을 얻습니다.
        korean_text, confidence = predict_sign_language_to_korean(
            payload.image_data, 
            payload.category, 
            client_ip=request.client.host if request.client else "default"
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        # 500 에러 세부 트래킹 로깅
        import traceback
        try:
            with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] ERROR IN INTERPRETER: {str(exc)}\n")
                f.write(traceback.format_exc())
                f.write("\n")
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(exc)}"
        )

    # 2단계: 인식된 한국어 문장을 영어 문장으로 번역합니다.
    english_text = translate_korean_to_english(korean_text)

    try:
        # 3단계: MongoDB의 통역기록 컬렉션에 실행 결과를 저장합니다.
        # DB 저장에 실패해도 사용자에게 번역 결과는 보여줄 수 있도록 오류를 응답에는 반영하지 않습니다.
        collection = get_interpreter_collection()
        collection.insert_one({
            "input_type": payload.input_type,
            "result_text": korean_text,
            "korean_text": korean_text,
            "english_text": english_text,
            "confidence": confidence,
            "language_from": payload.language_from,
            "language_to": payload.language_to,
            "user_id": payload.user_id,
            "created_at": datetime.now(timezone.utc),
        })
    except PyMongoError:
        # 예: MongoDB 서버 연결 실패, 컬렉션 쓰기 실패 등
        pass

    # 4단계: 프론트가 화면에 표시할 응답 JSON을 반환합니다.
    return TranslateResponseSchema(
        success=True,
        korean_text=korean_text,
        english_text=english_text,
        confidence=confidence,
    )

from typing import Union, List
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
            
        # 수형 일치 여부 검증 헬퍼
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
            rule_normalized = rule_shape.replace("·", ",").replace(" ", "")
            user_normalized = user_shape.replace("·", ",").replace(" ", "")
            return rule_normalized == user_normalized or rule_normalized in user_normalized or user_normalized in rule_normalized

        # Soft matching: 사용자가 캡처한 수어 단계들이 DB 규칙 데이터의 흐름과 얼마나 일치하는지 비율 계산
        matched_steps = 0
        total_checks = len(payload)
        
        for user_step in payload:
            r_user = user_step.get("right_hand", {})
            l_user = user_step.get("left_hand", {})
            user_uses_right = r_user.get("shape", "none") != "none"
            user_uses_left = l_user.get("shape", "none") != "none"
            
            step_matched = False
            # DB 시퀀스의 단계 중 하나라도 이 사용자 프레임과 매칭되는지 확인 (순서/속도 노이즈 완화)
            for rule_step in sequence:
                r_rule = rule_step.get("right_hand", {})
                l_rule = rule_step.get("left_hand", {})
                
                if isinstance(r_rule, str):
                    try: r_rule = json.loads(r_rule)
                    except: r_rule = {}
                if isinstance(l_rule, str):
                    try: l_rule = json.loads(l_rule)
                    except: l_rule = {}
                
                rule_uses_right = r_rule.get("shape", "none") != "none"
                rule_uses_left = l_rule.get("shape", "none") != "none"
                
                # 1. 사용 손 일치 검증
                if rule_uses_right != user_uses_right or rule_uses_left != user_uses_left:
                    continue
                    
                # 2. 수형 일치 검증
                shape_ok = True
                if rule_uses_right:
                    if not is_shape_compatible(r_rule.get("shape", ""), r_user.get("shape", "")):
                        shape_ok = False
                if rule_uses_left:
                    if not is_shape_compatible(l_rule.get("shape", ""), l_user.get("shape", "")):
                        shape_ok = False
                        
                if shape_ok:
                    step_matched = True
                    break
            
            if step_matched:
                matched_steps += 1

        match_rate = matched_steps / total_checks if total_checks > 0 else 0
        
        msg = f"[SOFT VALIDATOR] Word: '{word_name}' | Matched: {matched_steps}/{total_checks} | Rate: {match_rate:.2f}"
        try:
            with open(debug_log_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] {msg}\n")
        except Exception:
            pass
            
        # 매칭률이 40% 이상이거나, 아주 짧은 감지의 경우 최소 1개 이상 일치하면 유효하다고 판정
        if match_rate >= 0.40 or (matched_steps >= 1 and total_checks <= 2):
            return True
            
        return False
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


def generate_behavior_description_for_step(data: dict) -> str:
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
    
    pos_map = {
        "face": "얼굴", 
        "cheek": "뺨", 
        "chest": "가슴", 
        "belly": "배(배꼽)",
        "head": "머리",
        "forehead": "이마",
        "chin": "턱",
        "right_eye": "오른쪽 눈",
        "right_shoulder": "오른쪽 어깨",
        "shoulder": "어깨",
        "left_hand": "왼손",
        "right_hand": "오른손"
    }
    touch_map = {"contact": "에 접촉하고", "near": " 근처로 가져가고"}
    
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
        "left_right": "좌우로 흔드는 동작을 함",
        "up_down": "위아래로 흔드는 동작을 함",
        "leftward": "왼쪽으로 이동하는 동작을 함",
        "rightward": "오른쪽으로 이동하는 동작을 함",
        "forward": "앞으로 내미는 동작을 함",
        "forward_stroke": "앞으로 쳐내거나 튕기는 동작을 함",
        "freeze": "그 상태로 멈춤",
    }
    act_ko = act_map.get(act, "")
    
    if act_ko:
        sentence += f" + {act_ko}"
    else:
        sentence += " + 상태를 유지함"
        
    return sentence


def generate_behavior_description(payload: list) -> str:
    if not payload or len(payload) == 0:
        return "동작 감지 대기 중..."
    return generate_behavior_description_for_step(payload[0])


# 이미지 데이터(단일 혹은 리스트)를 입력받아 MediaPipe 랜드마크 분석 및 Azure OpenAI 추론을 통해 수어 문장을 인식합니다.
def predict_sign_language_to_korean(image_data_input: Union[str, list[str]], category: str = "개념", client_ip: str = "default") -> tuple[str, float]:
    if isinstance(image_data_input, str):
        image_data_list = [image_data_input]
    else:
        image_data_list = image_data_input

    # Decode and process all frames in the list
    frame_states = []
    
    # 디버깅 로그 경로
    debug_log_path = DEBUG_LOG_PATH
    
    for frame_idx, img_data in enumerate(image_data_list):
        if not img_data.startswith("data:image/"):
            continue
            
        try:
            header, encoded = img_data.split(",", 1)
            image_bytes = base64.b64decode(encoded)
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                continue
            
            # 디버깅을 위해 프론트로부터 수신한 이미지 중 마지막 이미지를 저장
            if frame_idx == len(image_data_list) - 1:
                cv2.imwrite(DEBUG_CAPTURE_PATH, img)
        except Exception as e:
            print(f"Failed to decode frame {frame_idx}: {e}")
            continue

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        hand_results = hands_detector.process(img_rgb)
        pose_results = pose_detector.process(img_rgb)

        # 신체 랜드마크 기준 x, y좌표 초기값 (포즈 미검출 시 절대 좌표 백업)
        nose_x, nose_y = 0.5, 0.3
        r_eye_x, r_eye_y = 0.45, 0.28
        l_eye_x, l_eye_y = 0.55, 0.28
        shoulder_y = 0.55
        r_shoulder_x, r_shoulder_y = 0.4, 0.55
        l_shoulder_x, l_shoulder_y = 0.6, 0.55
        hip_y = 0.8

        if pose_results.pose_landmarks:
            p_lms = pose_results.pose_landmarks.landmark
            nose_x = p_lms[0].x
            nose_y = p_lms[0].y
            r_eye_x = p_lms[5].x
            r_eye_y = p_lms[5].y
            l_eye_x = p_lms[2].x
            l_eye_y = p_lms[2].y
            shoulder_y = (p_lms[11].y + p_lms[12].y) / 2.0
            r_shoulder_x, r_shoulder_y = p_lms[12].x, p_lms[12].y
            l_shoulder_x, l_shoulder_y = p_lms[11].x, p_lms[11].y
            hip_y = (p_lms[23].y + p_lms[24].y) / 2.0

        r_shape, r_pos, r_touch, r_coord, r_scale = "none", "none", "none", None, 0.0
        l_shape, l_pos, l_touch, l_coord, l_scale = "none", "none", "none", None, 0.0

        r_avg_x, r_avg_y = 0.5, 0.5
        l_avg_x, l_avg_y = 0.5, 0.5
        has_right_hand = False
        has_left_hand = False

        if hand_results.multi_hand_landmarks and hand_results.multi_handedness:
            for idx, hand_handedness in enumerate(hand_results.multi_handedness):
                label = hand_handedness.classification[0].label # Left 또는 Right
                landmarks = hand_results.multi_hand_landmarks[idx].landmark
                coords = [(lm.x, lm.y) for lm in landmarks]
                
                avg_x = sum([lm.x for lm in landmarks]) / 21
                avg_y = sum([lm.y for lm in landmarks]) / 21
                
                # A) 손가락 펴짐 여부 판별 및 수형(Shape) 조합 알고리즘
                dx = landmarks[0].x - landmarks[9].x
                dy = landmarks[0].y - landmarks[9].y
                dz = landmarks[0].z - landmarks[9].z
                hand_scale = (dx*dx + dy*dy + dz*dz)**0.5
                if hand_scale == 0:
                    hand_scale = 0.001

                tdx = landmarks[4].x - landmarks[9].x
                tdy = landmarks[4].y - landmarks[9].y
                tdz = landmarks[4].z - landmarks[9].z
                thumb_to_mid = (tdx*tdx + tdy*tdy + tdz*tdz)**0.5
                
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

                if len(opened_fingers) == 0:
                    shape_str = "fist"
                elif len(opened_fingers) >= 4:
                    shape_str = "open_palm"
                else:
                    shape_str = "·".join(opened_fingers) + "지"
                
                # B) 손의 상대적 위치 계산
                # 세부적인 얼굴/머리/어깨/손 등 위치 정보 매핑
                pos_str = "none"
                forehead_y = nose_y - 0.08
                dist_to_forehead = ((avg_x - nose_x)**2 + (avg_y - forehead_y)**2)**0.5
                chin_y = nose_y + 0.12
                dist_to_chin = ((avg_x - nose_x)**2 + (avg_y - chin_y)**2)**0.5
                dist_to_nose = ((avg_x - nose_x)**2 + (avg_y - nose_y)**2)**0.5
                dist_to_r_eye = ((avg_x - r_eye_x)**2 + (avg_y - r_eye_y)**2)**0.5
                dist_to_r_shoulder = ((avg_x - r_shoulder_x)**2 + (avg_y - r_shoulder_y)**2)**0.5
                dist_to_l_shoulder = ((avg_x - l_shoulder_x)**2 + (avg_y - l_shoulder_y)**2)**0.5
                chest_hip_mid = (shoulder_y + hip_y) / 2.0
                
                if dist_to_r_eye < 0.08:
                    pos_str = "right_eye"
                elif dist_to_forehead < 0.07:
                    pos_str = "forehead"
                elif dist_to_chin < 0.06:
                    pos_str = "chin"
                elif dist_to_nose < 0.15:
                    pos_str = "face"
                elif avg_y < nose_y - 0.08:
                    pos_str = "head"
                elif dist_to_r_shoulder < 0.10:
                    pos_str = "right_shoulder"
                elif dist_to_l_shoulder < 0.10:
                    pos_str = "shoulder"
                elif abs(avg_y - shoulder_y) < 0.08:
                    pos_str = "shoulder"
                elif avg_y < chest_hip_mid:
                    pos_str = "chest"
                else:
                    pos_str = "none"

                # C) 접촉 판정
                touch_str = "none"
                if pos_str != "none":
                    target_x, target_y = None, None
                    if pos_str == "right_eye":
                        target_x, target_y = r_eye_x, r_eye_y
                    elif pos_str == "forehead":
                        target_x, target_y = nose_x, forehead_y
                    elif pos_str == "chin":
                        target_x, target_y = nose_x, chin_y
                    elif pos_str == "face":
                        target_x, target_y = nose_x, nose_y
                    elif pos_str == "head":
                        target_x, target_y = nose_x, nose_y - 0.1
                    elif pos_str == "right_shoulder":
                        target_x, target_y = r_shoulder_x, r_shoulder_y
                    elif pos_str == "shoulder":
                        target_x, target_y = l_shoulder_x, l_shoulder_y
                    elif pos_str == "chest":
                        target_x, target_y = nose_x, (shoulder_y + chest_hip_mid) / 2.0
                    
                    if target_x is not None and target_y is not None:
                        dist = ((avg_x - target_x)**2 + (avg_y - target_y)**2)**0.5
                        if dist < 0.07:
                            touch_str = "contact"
                        elif dist < 0.16:
                            touch_str = "near"

                # 스왑 적용 (MediaPipe Left 라벨 -> 사용자 기준 오른손)
                if label == "Left":
                    r_shape = shape_str
                    r_pos = pos_str
                    r_touch = touch_str
                    r_coord = coords[0] # 손목 기준
                    r_scale = hand_scale
                    r_avg_x, r_avg_y = avg_x, avg_y
                    has_right_hand = True
                else:
                    l_shape = shape_str
                    l_pos = pos_str
                    l_touch = touch_str
                    l_coord = coords[0]
                    l_scale = hand_scale
                    l_avg_x, l_avg_y = avg_x, avg_y
                    has_left_hand = True

            # D) 양손이 매우 가까운 경우 상호 위치 판정 (left_hand, right_hand)
            if has_right_hand and has_left_hand:
                dist_hands = ((r_avg_x - l_avg_x)**2 + (r_avg_y - l_avg_y)**2)**0.5
                if dist_hands < 0.12:
                    r_pos = "left_hand"
                    r_touch = "contact" if dist_hands < 0.07 else "near"
                    l_pos = "right_hand"
                    l_touch = "contact" if dist_hands < 0.07 else "near"

        frame_states.append({
            "r_shape": r_shape, "r_pos": r_pos, "r_touch": r_touch, "r_coord": r_coord, "r_scale": r_scale,
            "l_shape": l_shape, "l_pos": l_pos, "l_touch": l_touch, "l_coord": l_coord, "l_scale": l_scale
        })

    # 손이 전혀 감지되지 않았을 때 AI 모델 호출 없이 빠른 대기 상태 응답 반환
    all_none = all(f["r_shape"] == "none" and f["l_shape"] == "none" for f in frame_states)
    if all_none or not frame_states:
        return "동작 감지 대기 중... (카메라 앞에 손을 보여주세요)", 0.0

    # E) 프레임 간 상태 전이를 분석하여 다단계 단계(Step) 분할 및 액션 판정
    steps_grouped = []
    current_step_state = None
    current_step_frames = []

    for state in frame_states:
        state_repr = (state["r_shape"], state["r_pos"], state["r_touch"],
                      state["l_shape"], state["l_pos"], state["l_touch"])
        
        if current_step_state is None:
            current_step_state = state_repr
            current_step_frames = [state]
        elif state_repr == current_step_state:
            current_step_frames.append(state)
        else:
            steps_grouped.append({
                "state": current_step_state,
                "frames": current_step_frames
            })
            current_step_state = state_repr
            current_step_frames = [state]

    if current_step_frames:
        steps_grouped.append({
            "state": current_step_state,
            "frames": current_step_frames
        })

    # 노이즈 필터링: 너무 짧은 빈 단계를 필터링
    cleaned_steps = []
    for step in steps_grouped:
        st = step["state"]
        is_empty = (st[0] == "none" and st[3] == "none")
        if len(step["frames"]) < 2 and is_empty and len(steps_grouped) > 1:
            continue
        cleaned_steps.append(step)
        
    if not cleaned_steps:
        cleaned_steps = steps_grouped

    # 각 단계의 궤적 분석을 통한 액션 추출 함수
    def determine_action_from_trajectory(coords, scales, threshold=0.03) -> str:
        if len(coords) < 2:
            return "none"
        total_dx = coords[-1][0] - coords[0][0]
        total_dy = coords[-1][1] - coords[0][1]
        scale_ratio = scales[-1] / (scales[0] if scales[0] > 0 else 0.001)
        
        x_changes = 0
        y_changes = 0
        for i in range(2, len(coords)):
            dx1 = coords[i][0] - coords[i-1][0]
            dx2 = coords[i-1][0] - coords[i-2][0]
            if dx1 * dx2 < 0 and abs(dx1) > 0.005:
                x_changes += 1
            dy1 = coords[i][1] - coords[i-1][1]
            dy2 = coords[i-1][1] - coords[i-2][1]
            if dy1 * dy2 < 0 and abs(dy1) > 0.005:
                y_changes += 1

        if x_changes >= 2:
            return "left_right"
        if y_changes >= 2:
            return "none"
            
        if scale_ratio > 1.22:
            return "forward_stroke" if len(coords) < 5 else "forward"
            
        if abs(total_dy) > abs(total_dx) and abs(total_dy) > threshold:
            return "upward" if total_dy < 0 else "downward"
        elif abs(total_dx) > abs(total_dy) and abs(total_dx) > threshold:
            return "leftward" if total_dx < 0 else "none"
            
        max_dist = max([((c[0]-coords[0][0])**2 + (c[1]-coords[0][1])**2)**0.5 for c in coords])
        if max_dist < 0.015:
            return "freeze"
            
        return "none"

    # 최종 단계별 페이로드 구성
    final_steps = []
    for i, step in enumerate(cleaned_steps):
        r_shape, r_pos, r_touch, l_shape, l_pos, l_touch = step["state"]
        frames = step["frames"]
        
        r_coords = [f["r_coord"] for f in frames if f["r_coord"] is not None]
        l_coords = [f["l_coord"] for f in frames if f["l_coord"] is not None]
        r_scales = [f["r_scale"] for f in frames if f["r_scale"] is not None]
        l_scales = [f["l_scale"] for f in frames if f["l_scale"] is not None]
        
        act = "none"
        if r_shape != "none" and len(r_coords) >= 2:
            act = determine_action_from_trajectory(r_coords, r_scales)
        elif l_shape != "none" and len(l_coords) >= 2:
            act = determine_action_from_trajectory(l_coords, l_scales)
            
        step_dict = {
            "step": i + 1,
            "right_hand": {"shape": r_shape, "position": r_pos, "touching": r_touch},
            "left_hand": {"shape": l_shape, "position": l_pos, "touching": l_touch},
            "action": act
        }
        step_dict["description"] = generate_behavior_description_for_step(step_dict)
        final_steps.append(step_dict)

    print(f"DEBUG INPUT - Category: {category} | Payload: {json.dumps(final_steps, ensure_ascii=False)}")

    # 디버깅용 텍스트 로그 기록
    try:
        with open(debug_log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- [시작] Category: {category} ---\n")
            f.write(f"Processed Multi-Step Payload: {json.dumps(final_steps, ensure_ascii=False)}\n")
    except Exception:
        pass

    # 병렬 다중 매칭 후보 페이로드 구성 (노이즈 보정 후보 구성)
    candidates = []
    candidates.append(("original", final_steps))

    # 1) 접촉 노이즈 보정 후보 (contact <-> near 교차 대입)
    p_touch = []
    touch_modified = False
    for step in final_steps:
        step_copy = json.loads(json.dumps(step))
        for hand in ["right_hand", "left_hand"]:
            if step_copy[hand]["touching"] == "contact":
                step_copy[hand]["touching"] = "near"
                touch_modified = True
            elif step_copy[hand]["touching"] == "near":
                step_copy[hand]["touching"] = "contact"
                touch_modified = True
        p_touch.append(step_copy)
    if touch_modified:
        for step in p_touch:
            step["description"] = generate_behavior_description_for_step(step)
        candidates.append(("touch_alt", p_touch))

    # 2) 액션 움직임 노이즈 보정 후보
    p_action = []
    action_modified = False
    for step in final_steps:
        step_copy = json.loads(json.dumps(step))
        if step_copy["action"] != "none":
            step_copy["action"] = "none"
            action_modified = True
        p_action.append(step_copy)
    if action_modified:
        for step in p_action:
            step["description"] = generate_behavior_description_for_step(step)
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

    # 카테고리 기반 화이트리스트 단어 목록 조회
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

    # 최종 매칭 선택
    final_cleaned = None
    final_raw = None
    selected_name = None
    selected_payload = None

    for name, p, raw, cleaned in results:
        if cleaned and "동작 감지 대기 중" not in cleaned:
            is_allowed = False
            if not allowed_words:
                is_allowed = True
            else:
                for allowed in allowed_words:
                    if cleaned in allowed or allowed in cleaned:
                        cleaned = allowed
                        is_allowed = True
                        break
            
            if is_allowed:
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

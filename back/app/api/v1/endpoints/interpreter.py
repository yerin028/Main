import random
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pymongo.errors import PyMongoError

from app.core.mongo_database import get_interpreter_collection
from app.schemas.interpreter import TranslateRequestSchema, TranslateResponseSchema

# APIRouter는 기능별 API 주소를 묶는 FastAPI 도구입니다.
# 이 파일에서는 /interpreter 아래에 들어갈 수어통역 API들을 정의합니다.
router = APIRouter()


# 현재는 실제 AI 모델이 없기 때문에 임시 mock 함수로 만들어 둔 부분입니다.
# 나중에 MediaPipe, TensorFlow, PyTorch 모델을 연결할 때는 이 함수 내부를 교체하면 됩니다.
# 입력: 프론트가 보낸 base64 이미지
# 출력: 인식된 한국어 문장, 신뢰도
def predict_sign_language_to_korean(image_data: str) -> tuple[str, float]:
    # 프론트에서 canvas.toDataURL()로 보낸 값은 data:image/jpeg;base64,... 형태입니다.
    # 이미지가 아닌 값이 들어오면 잘못된 요청으로 판단합니다.
    if not image_data.startswith("data:image/"):
        raise ValueError("image_data must be a base64 data URL.")

    # 실제 모델 대신 테스트용으로 사용할 예시 결과입니다.
    # random.choice를 사용해 매 요청마다 예시 문장 중 하나가 반환됩니다.
    sample_results = [
        ("안녕하세요", 0.96),
        ("만나서 반갑습니다", 0.94),
        ("감사합니다", 0.95),
        ("도움이 필요합니다", 0.93),
    ]
    return random.choice(sample_results)


# 한국어 인식 결과를 영어로 바꾸는 함수입니다.
# 지금은 간단한 딕셔너리 매핑이지만, 추후 번역 API나 번역 모델로 교체할 수 있습니다.
def translate_korean_to_english(korean_text: str) -> str:
    translations = {
        "안녕하세요": "Hello.",
        "만나서 반갑습니다": "Nice to meet you.",
        "감사합니다": "Thank you.",
        "도움이 필요합니다": "I need help.",
    }
    return translations.get(korean_text, korean_text)


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
):
    # image_data가 비어 있으면 수어 인식을 할 수 없으므로 400 Bad Request를 반환합니다.
    if not payload.image_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="image_data 값이 필요합니다.",
        )

    try:
        # 1단계: 카메라 이미지에서 수어를 인식해 한국어 문장을 얻습니다.
        korean_text, confidence = predict_sign_language_to_korean(payload.image_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

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

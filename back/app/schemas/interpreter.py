from pydantic import BaseModel, Field


# Pydantic 스키마는 FastAPI에서 "요청/응답 데이터의 모양"을 정의하는 클래스입니다.
# 프론트에서 어떤 JSON을 보내야 하는지, 백엔드가 어떤 JSON을 돌려주는지 명확하게 정해 줍니다.
class TranslateRequestSchema(BaseModel):
    # 프론트에서 카메라 화면을 캡처한 base64 이미지 문자열입니다.
    # 실제 AI 모델을 붙이면 이 값을 디코딩해서 모델 입력 이미지로 사용할 수 있습니다.
    image_data: str = Field(..., description="Base64 encoded camera frame.")

    # 현재는 카메라 입력만 사용하지만, 나중에 이미지 업로드/동영상 업로드 등을 추가할 수 있어 둔 필드입니다.
    input_type: str = Field(default="camera", description="Translation input type.")

    # 원본 언어와 번역 대상 언어입니다.
    # 수어 인식 결과를 한국어로 만들고, 그 한국어를 영어로 번역하는 흐름이라 기본값은 ko -> en입니다.
    language_from: str = Field(default="ko", description="Source language code.")
    language_to: str = Field(default="en", description="Target language code.")

    # 로그인 기능과 연결되면 사용자별 통역 기록을 남길 수 있습니다.
    # 아직 로그인 사용자 정보를 붙이지 않아도 API가 동작하도록 None을 허용합니다.
    user_id: int | None = Field(default=None, description="Optional logged-in user id.")


# 번역 API가 프론트로 돌려주는 응답 데이터 구조입니다.
class TranslateResponseSchema(BaseModel):
    # 요청 처리 성공 여부입니다.
    success: bool

    # 수어 인식 모델이 판단한 한국어 문장입니다.
    korean_text: str

    # 한국어 문장을 영어로 번역한 결과입니다.
    english_text: str

    # 인식 결과에 대한 신뢰도입니다. 0.0 ~ 1.0 사이 값으로 사용합니다.
    confidence: float

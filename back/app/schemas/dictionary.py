from pydantic import BaseModel  # FastAPI 응답 JSON 구조를 정의하기 위해 사용하는 Pydantic 기본 클래스입니다.


class DictionarySchema(BaseModel):
    # 프론트로 전달할 수어 사전 데이터의 응답 구조입니다.
    # Swagger의 Response body 예시도 이 스키마를 기준으로 표시됩니다.

    # 수어 사전 데이터의 고유 ID입니다.
    dictionary_id: int

    # 수어 단어가 속한 카테고리 이름입니다.
    category_name: str

    # 수어 단어명입니다.
    word_name: str

    # 수어 동작 설명입니다.
    definition: str

    # 수어 영상 mp4 주소입니다.
    # 영상 URL이 없는 데이터도 있을 수 있으므로 None을 허용합니다.
    video_url: str | None = None

    # SQLAlchemy 모델 객체(DictionaryModel)를 Pydantic 응답 스키마로 변환할 수 있게 하는 설정입니다.
    # 이 설정이 있어야 endpoint에서 DictionaryModel 객체를 그대로 return해도 JSON으로 변환됩니다.
    model_config = {"from_attributes": True}

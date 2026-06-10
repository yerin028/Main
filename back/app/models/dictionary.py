from pydantic import BaseModel  # MongoDB 문서 구조를 코드에서 확인하기 위해 사용하는 Pydantic 기본 클래스입니다.

class DictionaryDocument(BaseModel):
    # MongoDB Dictionary 컬렉션에 저장되는 수어표현검색 문서 구조입니다.

    # 수어 사전 데이터의 고유 ID입니다.
    # MongoDB에서는 자동 증가 컬럼이 없으므로 endpoint에서 직접 숫자를 넣어줍니다.
    dictionary_id: int

    # 수어 단어가 속한 카테고리 이름입니다.
    # 예: 기타, 식생활, 나라명 및 지명
    category_name: str

    # 수어 단어명입니다.
    # 예: 강원도, 대장, 빵집
    word_name: str

    # 수어 동작 설명입니다.
    definition: str

    # 수어 영상 mp4 주소입니다.
    # 국립수어원 API의 subDescription 값이 이 필드에 저장됩니다.
    video_url: str | None = None

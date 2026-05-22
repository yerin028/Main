from sqlalchemy import Column, Integer, String, Text  # DICTIONARY 테이블 컬럼 타입을 정의하기 위해 사용합니다.

from app.core.mysql_database import Base  # SQLAlchemy 모델이 상속받는 기본 클래스입니다.


class DictionaryModel(Base):
    # 이 클래스가 MySQL의 DICTIONARY 테이블과 연결된다는 뜻입니다.
    __tablename__ = "DICTIONARY"

    # 수어 사전 데이터의 고유 ID입니다.
    # primary_key=True라서 테이블의 기본키 역할을 합니다.
    dictionary_id = Column(Integer, primary_key=True, index=True)

    # 수어 단어가 속한 카테고리 이름입니다.
    # 예: 기타, 식생활, 나라명 및 지명
    category_name = Column(String(100), nullable=False)

    # 수어 단어명입니다.
    # 예: 강원도, 대장, 빵집
    word_name = Column(String(255), nullable=False)

    # 수어 동작 설명입니다.
    # 설명이 길 수 있으므로 Text 타입을 사용합니다.
    definition = Column(Text, nullable=False)

    # 수어 영상 mp4 주소입니다.
    # 국립수어원 API의 subDescription 값이 이 컬럼에 저장됩니다.
    video_url = Column(String(255))

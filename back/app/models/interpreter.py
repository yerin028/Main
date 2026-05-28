from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.core.mysql_database import Base


# SQLAlchemy 모델은 파이썬 클래스와 DB 테이블을 연결해 주는 역할을 합니다.
# 이 클래스는 ERD의 Interpreter_Log(통역기록) 테이블에 해당합니다.
class InterpreterLog(Base):
    # 실제 MySQL에 생성/조회될 테이블 이름입니다.
    __tablename__ = "interpreter_log"

    # 통역기록ID: 각 통역 기록을 구분하는 기본키(PK)입니다.
    # autoincrement=True라서 새 기록이 저장될 때 DB가 번호를 자동으로 증가시킵니다.
    log_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 입력유형: 현재는 camera를 저장합니다.
    # 나중에 image, video 같은 입력 방식이 추가되면 이 컬럼으로 구분할 수 있습니다.
    input_type = Column(String(50), nullable=False, default="camera")

    # 번역결과: 수어 인식 결과인 한국어 문장을 저장합니다.
    # ERD의 result_text 컬럼에 해당합니다.
    result_text = Column(Text, nullable=False)

    # 원본언어/번역언어: ko -> en 같은 언어 흐름을 저장합니다.
    language_from = Column(String(10), nullable=False, default="ko")
    language_to = Column(String(10), nullable=False, default="en")

    # 생성일시: DB 서버 시간이 자동으로 들어갑니다.
    # 사용자가 통역을 실행한 시점을 기록하기 위해 필요합니다.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 사용자ID: 로그인 사용자의 기록을 연결하기 위한 외래키 용도입니다.
    # 현재는 로그인 연동 전에도 동작해야 하므로 nullable=True로 둡니다.
    user_id = Column(Integer, nullable=True)

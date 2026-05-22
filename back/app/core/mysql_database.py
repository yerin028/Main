from sqlalchemy import create_engine  # SQLAlchemy가 MySQL과 연결할 engine을 만들기 위해 사용합니다.
from sqlalchemy.orm import declarative_base, sessionmaker  # DB 모델 기준 클래스와 DB 세션 생성기를 만들기 위해 사용합니다.

from app.core.config import settings  # config.py에서 env 기반 DB 접속 정보를 가져옵니다.


# MySQL 연결 engine입니다.
# settings.database_url은 config.py에서 사용자명, 비밀번호, host, DB 이름을 조합해서 만든 값입니다.
# pool_pre_ping=True는 오래된 DB 연결이 끊겼는지 먼저 확인해서 연결 오류를 줄여줍니다.
engine = create_engine(settings.database_url, pool_pre_ping=True)

# API 요청마다 DB 작업에 사용할 세션을 만들어주는 생성기입니다.
# autocommit=False라서 db.commit()을 호출해야 실제 저장이 확정됩니다.
# autoflush=False라서 의도하지 않은 시점에 자동 반영되는 일을 줄입니다.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# SQLAlchemy 모델 클래스들이 상속받는 기본 클래스입니다.
# models/dictionary.py의 DictionaryModel이 이 Base를 상속해서 DB 테이블 모델이 됩니다.
Base = declarative_base()


def get_db():
    # FastAPI endpoint에서 Depends(get_db)로 호출되는 DB 세션 제공 함수입니다.
    # 요청이 들어올 때 세션을 하나 만들고, 요청 처리가 끝나면 반드시 닫아줍니다.
    db = SessionLocal()
    try:
        # yield로 endpoint 함수에 db 세션을 넘겨줍니다.
        yield db
    finally:
        # 요청이 성공하든 실패하든 DB 세션을 닫아 연결 누수를 막습니다.
        db.close()

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 루트 폴더에 있는 .env 로드
current_dir = os.path.dirname(os.path.abspath(__file__))
# app/core/database 위치이므로 부모의 부모 폴더(../../)로 이동해서 .env를 찾음
env_path = os.path.join(current_dir, "..", "..", ".env")
load_dotenv(env_path)

DB_HOST = os.getenv("DB_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DB = os.getenv("MYSQL_DB")

# MySQL 연결 URL 및 엔진 설정
MYSQL_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{DB_HOST}:3306/{MYSQL_DB}"
engine = create_engine(MYSQL_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# ==========================================
# [MySQL 테이블 모델 정의]
# ==========================================

# 사용자 테이블 구조
# class User(Base):
#     __tablename__ = "users"
    
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     user_id = Column(String(50), nullable=False, unique=True)     # 사용자 ID
#     created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# API 개발할 때 팀원들이 DB 세션을 획득하기 위해 쓸 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


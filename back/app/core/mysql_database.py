# MySQL(SQLAlchemy) 데이터베이스 연결을 설정하고 관리하는 파일입니다.
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 데이터베이스 연결 URL 설정
DATABASE_URL = "mysql+pymysql://root:password@localhost:3306/sign_language_db"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
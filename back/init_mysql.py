from app.core.mysql_database import engine, Base

def main():
    print("MySQL 테이블 자동 생성을 시작")
    Base.metadata.create_all(bind=engine)
    print("MySQL 인프라 빌드 완료")

if __name__ == "__main__":
    main()
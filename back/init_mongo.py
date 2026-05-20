from datetime import datetime, timezone
from app.core.mongo_database import get_mongo_collection

def main():
    print("MongoDB 지연 생성 초기화를 시작")
    log_collection = get_mongo_collection()
    
    dummy_data = {
        "message": "MongoDB 보안 시스템 초기 빌드 완료",
        "initialized_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    }
    
    if log_collection.count_documents({}) == 0:
        log_collection.insert_one(dummy_data)
        print("MongoDB: 데이터베이스 및 컬렉션 주머니 생성 완료")
    else:
        print("MongoDB: 이미 데이터가 존재하므로 단계를 건너뜁니다.")

if __name__ == "__main__":
    main()
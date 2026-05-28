import os
from dotenv import load_dotenv
from pymongo import MongoClient

# 1. 현재 파일 위치 기준 절대 경로로 .env 로드
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, "..", "..", ".env")
load_dotenv(env_path)

MONGODB_URI = os.getenv("MONGODB_URI")

if not MONGODB_URI:
    raise ValueError("MONGODB_URI를 .env 파일에서 찾을 수 없습니다!")

# 2. 클라우드 MongoDB 접속 엔진 설정
client = MongoClient(MONGODB_URI)
db = client.get_default_database()


# ==========================================
# [MongoDB 공용 컬렉션 창구] - 주석 해제 (init용)
# ==========================================
def get_mongo_collection():
    return db["recognition_logs"]


def get_dictionary_collection():
    # 수어표현검색 데이터가 저장되는 MongoDB 컬렉션입니다.
    return db["Dictionary"]


# ==========================================
# [MongoDB 데이터 삽입 기능 가이드] - 내부 주석화
# ==========================================
def insert_recognition_log(user_id: str, recognized_word: str, accuracy: float, landmark_data: dict = None):
    #  from datetime import datetime, timezone
    #  log_collection = get_mongo_collection()
    #  
    #  # MongoDB에 저장할 서류(데이터)의 표준 스키마 구조입니다.
    #  log_document = {
    #      "user_id": user_id,                # 유저 고유 ID (형식: String)
    #      "recognized_word": recognized_word,  # 인식된 수어 단어명 (형식: String)
    #      "accuracy": round(accuracy, 4),    # 인식 정확도 (형식: Float, 소수점 4자리 제한)
    #      "detected_at": datetime.now(timezone.utc),  # 데이터가 저장된 글로벌 표준 시간
    #      "landmark_points": landmark_data if landmark_data else {}  # 손가락 관절 좌표 벡터 데이터 (형식: Dict)
    #  }
    #  
    #  # 주머니에 서류 밀어 넣기
    #  result = log_collection.insert_one(log_document)
    #  print(f"[MongoDB 로그 기록 성공] ID: {result.inserted_id}")
    #  return result.inserted_id
    
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.api import api_router

# FastAPI 애플리케이션 객체입니다.
# uvicorn app.main:app --reload 명령을 실행하면 이 app 객체가 서버로 실행됩니다.
app = FastAPI(title="Sign Language Translation API")

# CORS 설정입니다.
# 프론트엔드(Vite)는 보통 5173 포트에서 실행되고,
# 백엔드(FastAPI)는 보통 8000 포트에서 실행됩니다.
# 브라우저는 포트가 다르면 다른 출처(origin)라고 보기 때문에,
# 프론트가 백엔드 API를 호출할 수 있도록 허용 목록에 넣어야 합니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 서버가 켜져 있는지 간단히 확인하는 기본 테스트 주소입니다.
@app.get("/")
def root():
    return {"message": "FastAPI server is running."}


# 모든 v1 API 앞에 /api/v1을 붙입니다.
# 예: /interpreter/translate -> /api/v1/interpreter/translate
app.include_router(api_router, prefix="/api/v1")

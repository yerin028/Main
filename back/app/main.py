from fastapi import FastAPI  # FastAPI 백엔드 애플리케이션 객체를 만들기 위해 사용합니다.
from fastapi.middleware.cors import CORSMiddleware  # 프론트엔드 localhost 요청을 허용하기 위한 CORS 설정 도구입니다.

from app.api.v1.endpoints.dictionary import router as dictionary_router  # 수어표현검색 API 라우터를 main에 직접 등록하기 위해 가져옵니다.
from app.api.api import api_router

# FastAPI 앱을 생성합니다.
# title 값은 Swagger 문서(/docs) 상단에 표시되는 API 이름입니다.
app = FastAPI(title="WITH API")

# CORS 설정입니다.
# 프론트엔드 개발 서버가 5173 포트에서 실행되므로 해당 주소의 요청을 허용합니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # 브라우저에서 localhost로 프론트에 접속했을 때 허용합니다.
        "http://127.0.0.1:5173",  # 브라우저에서 127.0.0.1로 프론트에 접속했을 때 허용합니다.
    ],
    allow_credentials=True,  # 쿠키나 인증 정보가 포함된 요청도 허용할 수 있게 합니다.
    allow_methods=["*"],  # GET, POST, PUT 등 모든 HTTP 메서드를 허용합니다.
    allow_headers=["*"],  # 프론트 요청에 포함되는 모든 header를 허용합니다.
)

# 수어표현검색 endpoint들을 FastAPI 앱에 등록합니다.
# dictionary_router 안의 최종 API 주소는 /api/v1/dictionary 로 시작합니다.
app.include_router(dictionary_router)
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    # 서버가 켜져 있는지 확인하는 기본 테스트 API입니다.
    # 브라우저에서 http://127.0.0.1:8000/ 로 접속하면 이 메시지가 나옵니다.
    return {"message": "WITH API"}


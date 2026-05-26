from fastapi import APIRouter

from app.api.v1.endpoints import interpreter, lessons

# api_router는 여러 기능별 라우터를 하나로 모으는 중앙 라우터입니다.
# main.py에서 이 라우터를 /api/v1 prefix로 등록합니다.
api_router = APIRouter()

# interpreter.router 안의 주소 앞에 /interpreter를 붙입니다.
# 예를 들어 interpreter.py에 "/translate"가 있으면
# 최종 주소는 /api/v1/interpreter/translate가 됩니다.
api_router.include_router(
    interpreter.router,
    prefix="/interpreter",
    tags=["interpreter"],
)

api_router.include_router(
    lessons.router,
    prefix="/lessons",
    tags=["lessons"],
)

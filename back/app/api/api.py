from fastapi import APIRouter  # 여러 endpoint 라우터를 하나로 묶을 때 사용하는 FastAPI 라우터입니다.

from app.api.v1.endpoints import auth, interpreter, lessons  # 공통 api_router로 묶을 endpoint 파일들을 가져옵니다.

# 여러 기능의 router를 한 번에 모아둘 수 있는 공통 API 라우터입니다.
# 현재 main.py에서는 팀 규칙에 맞춰 dictionary_router를 직접 include하고 있습니다.
# 그래도 나중에 api_router 방식으로 다시 묶을 수 있도록 파일은 유지합니다.
api_router = APIRouter()


# dictionary.router는 main.py에서 직접 등록합니다.
# 여기에도 dictionary.router를 넣으면 /api/v1/dictionary와 /api/v1/api/v1/dictionary가 중복 등록될 수 있습니다.
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
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
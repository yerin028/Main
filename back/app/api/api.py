from fastapi import APIRouter  # 여러 endpoint 라우터를 하나로 묶을 때 사용하는 FastAPI 라우터입니다.

from app.api.v1.endpoints import auth, interpreter,dictionary  # 수어표현검색 endpoint 파일을 가져옵니다.


# 여러 기능의 router를 한 번에 모아둘 수 있는 공통 API 라우터입니다.
# 현재 main.py에서는 팀 규칙에 맞춰 dictionary_router를 직접 include하고 있습니다.
# 그래도 나중에 api_router 방식으로 다시 묶을 수 있도록 파일은 유지합니다.
api_router = APIRouter()

# dictionary.router는 이미 prefix="/api/v1/dictionary"를 가지고 있습니다.
# 그래서 여기서는 prefix를 추가하지 않아야 /api/v1/api/v1/dictionary처럼 중복되지 않습니다.
api_router.include_router(dictionary.router)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
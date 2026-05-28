from fastapi import APIRouter  # 여러 endpoint 라우터를 하나로 묶을 때 사용하는 FastAPI 라우터입니다.
<<<<<<< Updated upstream
from app.api.v1.endpoints import auth, interpreter,dictionary,payment  # 수어표현검색 endpoint 파일을 가져옵니다.
from app.api.v1.endpoints import auth, interpreter, lessons  # 공통 api_router로 묶을 endpoint 파일들을 가져옵니다.
=======

from app.api.v1.endpoints import auth, interpreter, lessons, payment, quiz
>>>>>>> Stashed changes

api_router = APIRouter()

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
api_router.include_router(payment.router, prefix="/payment", tags=["payment"])
api_router.include_router(quiz.router, prefix="/quiz", tags=["quiz"])

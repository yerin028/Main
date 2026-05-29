from fastapi import APIRouter

from app.api.v1.endpoints import auth, cs, interpreter, lessons, payment, quiz, refund

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
api_router.include_router(cs.router, prefix="/cs", tags=["cs"])
api_router.include_router(refund.router, prefix="/refunds", tags=["refunds"])

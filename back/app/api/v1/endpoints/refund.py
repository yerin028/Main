from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.mysql_database import engine, get_db
from app.models.cs import Refund
from app.schemas.cs import RefundCreate, RefundSchema

router = APIRouter()


def ensure_refund_table():
    Refund.__table__.create(bind=engine, checkfirst=True)


@router.post(
    "",
    response_model=RefundSchema,
    status_code=status.HTTP_201_CREATED,
)
def create_refund(
    refund_create: RefundCreate,
    db: Session = Depends(get_db),
):
    ensure_refund_table()

    refund = Refund(
        reason=refund_create.reason,
        status="신청",
        payment_id=refund_create.payment_id,
    )

    try:
        db.add(refund)
        db.commit()
        db.refresh(refund)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create refund.",
        ) from error

    return refund

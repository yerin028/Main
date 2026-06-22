from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.mysql_database import get_db
from app.models.payment import Payment, Refund
from app.models.users import User
from app.schemas.cs import RefundCreate, RefundSchema

router = APIRouter()


def serialize_refund(refund: Refund, payment: Payment = None, user: User = None):
    return RefundSchema(
        refund_id=refund.refund_id,
        reason=refund.reason,
        status=refund.status,
        request_at=refund.request_at,
        processed_at=refund.processed_at,
        payment_id=refund.payment_id,
        user_id=user.user_id if user else None,
        user_name=user.name if user else None,
        user_email=user.email if user else None,
        payment_amount=payment.amount if payment else None,
        payment_status=payment.payment_status if payment else None,
        toss_order_id=payment.toss_order_id if payment else None,
        toss_payment_key=payment.toss_payment_key if payment else None,
    )


@router.post(
    "",
    response_model=RefundSchema,
    status_code=status.HTTP_201_CREATED,
)
def create_refund(
    refund_create: RefundCreate,
    db: Session = Depends(get_db),
):
    payment = None
    user = None

    if refund_create.payment_id:
        payment = db.query(Payment).filter(Payment.payment_id == refund_create.payment_id).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found.")

    user_id = refund_create.user_id or (payment.user_id if payment else None)
    if user_id:
        user = db.query(User).filter(User.user_id == user_id).first()

    refund = Refund(
        reason=refund_create.reason,
        status="신청",
        request_at=datetime.now(timezone.utc),
        payment_id=refund_create.payment_id,
    )

    try:
        db.add(refund)
        db.commit()
        db.refresh(refund)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create refund.") from error

    return serialize_refund(refund, payment, user)


@router.patch(
    "/{refund_id}/approve",
    response_model=RefundSchema,
)
def approve_refund(
    refund_id: int,
    db: Session = Depends(get_db),
):
    refund = (
        db.query(Refund)
        .filter(Refund.refund_id == refund_id)
        .first()
    )

    if not refund:
        raise HTTPException(
            status_code=404,
            detail="Refund not found."
        )

    payment = (
        db.query(Payment)
        .filter(Payment.payment_id == refund.payment_id)
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found."
        )

    user = (
        db.query(User)
        .filter(User.user_id == payment.user_id)
        .first()
    )

    try:
        payment.payment_status = "REFUNDED"

        refund.status = "승인"
        refund.processed_at = datetime.now(timezone.utc)

        if user:
            user.subscription_end_date = None
            user.billing_key = None

        db.commit()

        db.refresh(refund)
        db.refresh(payment)

    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to approve refund."
        ) from error

    return serialize_refund(refund, payment, user)


@router.get(
    "",
    response_model=list[RefundSchema],
    status_code=status.HTTP_200_OK,
)
def read_refunds(db: Session = Depends(get_db)):
    refunds = db.query(Refund).order_by(Refund.refund_id).all()
    result = []
    for refund in refunds:
        payment = db.query(Payment).filter(Payment.payment_id == refund.payment_id).first() if refund.payment_id else None
        user = db.query(User).filter(User.user_id == payment.user_id).first() if payment else None
        result.append(serialize_refund(refund, payment, user))
    return result
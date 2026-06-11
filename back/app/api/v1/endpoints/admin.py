import base64
import os
import httpx
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.mysql_database import get_db
from app.models.payment import Payment, Refund
from app.models.users import User
from app.schemas.cs import RefundSchema, RefundStatusUpdate
from app.schemas.payment import PaymentSchema

router = APIRouter()

TOSS_CANCEL_URL = "https://api.tosspayments.com/v1/payments/{}/cancel"


def get_toss_authorization_header():
    toss_secret_key = os.getenv("TOSS_SECRET_KEY")
    encoded_key = base64.b64encode(f"{toss_secret_key}:".encode("utf-8")).decode("utf-8")
    return f"Basic {encoded_key}"


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


@router.get(
    "/payments",
    response_model=list[PaymentSchema],
    status_code=status.HTTP_200_OK,
)
def read_admin_payments(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return (
        db.query(Payment)
        .order_by(Payment.payment_id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )


@router.get(
    "/refunds",
    response_model=list[RefundSchema],
    status_code=status.HTTP_200_OK,
)
def read_admin_refunds(db: Session = Depends(get_db)):
    refunds = db.query(Refund).order_by(Refund.refund_id).all()
    result = []
    for refund in refunds:
        payment = db.query(Payment).filter(Payment.payment_id == refund.payment_id).first() if refund.payment_id else None
        user = db.query(User).filter(User.user_id == payment.user_id).first() if payment else None
        result.append(serialize_refund(refund, payment, user))
    return result


@router.put(
    "/refunds",
    response_model=RefundSchema,
    status_code=status.HTTP_200_OK,
)
async def update_admin_refund(
    refund_update: RefundStatusUpdate,
    db: Session = Depends(get_db),
):
    if refund_update.status not in {"승인됨", "거절됨"}:
        raise HTTPException(status_code=400, detail="Refund status must be 승인됨 or 거절됨.")

    refund = db.query(Refund).filter(Refund.refund_id == refund_update.refund_id).first()
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found.")

    if refund.status in {"승인됨", "거절됨"}:
        payment = db.query(Payment).filter(Payment.payment_id == refund.payment_id).first() if refund.payment_id else None
        user = db.query(User).filter(User.user_id == payment.user_id).first() if payment else None
        return serialize_refund(refund, payment, user)

    payment = db.query(Payment).filter(Payment.payment_id == refund.payment_id).first() if refund.payment_id else None
    user = db.query(User).filter(User.user_id == payment.user_id).first() if payment else None

    # 승인 시 토스 환불 API 호출
    if refund_update.status == "승인됨":
        if not payment or not payment.toss_payment_key:
            raise HTTPException(status_code=400, detail="토스 결제 키를 찾을 수 없습니다.")

        headers = {
            "Authorization": get_toss_authorization_header(),
            "Content-Type": "application/json",
        }
        payload = {"cancelReason": refund.reason or "고객 요청"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            toss_response = await client.post(
                TOSS_CANCEL_URL.format(payment.toss_payment_key),
                headers=headers,
                json=payload,
            )

        if toss_response.status_code >= 400:
            raise HTTPException(
                status_code=toss_response.status_code,
                detail=toss_response.json(),
            )
        
        if user:
            user.subscription_end_date = None
        payment.payment_status = "CANCELLED"

    refund.status = refund_update.status
    refund.processed_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(refund)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update refund.") from error

    return serialize_refund(refund, payment, user)
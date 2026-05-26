import base64
import os
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.mysql_database import engine, get_db
from app.models.payment import PaymentModel
from app.schemas.payment import (
    PaymentConfirmSchema,
    PaymentCreateSchema,
    PaymentSchema,
    PaymentStatusUpdateSchema,
)

load_dotenv()

router = APIRouter()
TOSS_CONFIRM_URL = "https://api.tosspayments.com/v1/payments/confirm"


def ensure_payment_table():
    PaymentModel.__table__.create(bind=engine, checkfirst=True)


def get_toss_authorization_header():
    toss_secret_key = os.getenv("TOSS_SECRET_KEY")

    if not toss_secret_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TOSS_SECRET_KEY is not configured.",
        )

    encoded_key = base64.b64encode(f"{toss_secret_key}:".encode("utf-8")).decode("utf-8")
    return f"Basic {encoded_key}"


def parse_toss_datetime(date_text: str | None):
    if not date_text:
        return None

    return datetime.fromisoformat(date_text.replace("Z", "+00:00"))


@router.post(
    "",
    response_model=PaymentSchema,
    status_code=status.HTTP_201_CREATED,
)
def create_payment(
    payment_create: PaymentCreateSchema,
    db: Session = Depends(get_db),
):
    ensure_payment_table()

    payment = PaymentModel(
        amount=payment_create.amount,
        payment_status=payment_create.payment_status,
        payment_method=payment_create.payment_method,
        toss_order_id=payment_create.toss_order_id,
        user_id=payment_create.user_id,
    )

    try:
        db.add(payment)
        db.commit()
        db.refresh(payment)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment.",
        ) from error

    return payment


@router.post(
    "/confirm",
    response_model=PaymentSchema,
    status_code=status.HTTP_200_OK,
)
async def confirm_payment(
    payment_confirm: PaymentConfirmSchema,
    db: Session = Depends(get_db),
):
    ensure_payment_table()

    headers = {
        "Authorization": get_toss_authorization_header(),
        "Content-Type": "application/json",
    }
    payload = {
        "paymentKey": payment_confirm.payment_key,
        "orderId": payment_confirm.order_id,
        "amount": payment_confirm.amount,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        toss_response = await client.post(TOSS_CONFIRM_URL, headers=headers, json=payload)

    toss_data = toss_response.json()

    if toss_response.status_code >= 400:
        raise HTTPException(
            status_code=toss_response.status_code,
            detail=toss_data,
        )

    payment = (
        db.query(PaymentModel)
        .filter(PaymentModel.toss_order_id == payment_confirm.order_id)
        .first()
    )

    if payment is None:
        payment = PaymentModel(
            toss_order_id=payment_confirm.order_id,
            user_id=payment_confirm.user_id,
        )
        db.add(payment)

    payment.amount = toss_data.get("totalAmount", payment_confirm.amount)
    payment.payment_status = toss_data.get("status", "DONE")
    payment.payment_method = toss_data.get("method")
    payment.payment_key = toss_data.get("paymentKey", payment_confirm.payment_key)
    payment.paid_at = parse_toss_datetime(toss_data.get("approvedAt"))

    try:
        db.commit()
        db.refresh(payment)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save confirmed payment.",
        ) from error

    return payment


@router.get(
    "",
    response_model=list[PaymentSchema],
    status_code=status.HTTP_200_OK,
)
def read_payments(
    user_id: int | None = Query(default=None, description="Filter payments by user id."),
    page: int = Query(default=1, ge=1, description="Payment page number."),
    size: int = Query(default=20, ge=1, le=100, description="Payments per page."),
    db: Session = Depends(get_db),
):
    ensure_payment_table()

    query = db.query(PaymentModel)

    if user_id is not None:
        query = query.filter(PaymentModel.user_id == user_id)

    return (
        query.order_by(PaymentModel.payment_id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )


@router.get(
    "/{payment_id}",
    response_model=PaymentSchema,
    status_code=status.HTTP_200_OK,
)
def read_payment(
    payment_id: int,
    db: Session = Depends(get_db),
):
    ensure_payment_table()

    payment = (
        db.query(PaymentModel)
        .filter(PaymentModel.payment_id == payment_id)
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    return payment


@router.patch(
    "/{payment_id}/status",
    response_model=PaymentSchema,
    status_code=status.HTTP_200_OK,
)
def update_payment_status(
    payment_id: int,
    payment_update: PaymentStatusUpdateSchema,
    db: Session = Depends(get_db),
):
    ensure_payment_table()

    payment = (
        db.query(PaymentModel)
        .filter(PaymentModel.payment_id == payment_id)
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    payment.payment_status = payment_update.payment_status

    if payment_update.payment_method is not None:
        payment.payment_method = payment_update.payment_method

    if payment_update.paid_at is not None:
        payment.paid_at = payment_update.paid_at
    elif payment_update.payment_status.upper() == "PAID":
        payment.paid_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(payment)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update payment.",
        ) from error

    return payment

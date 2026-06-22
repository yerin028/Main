import base64
import os
import uuid
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.mysql_database import engine, get_db
from app.models.payment import Payment
from app.models.users import User
from app.schemas.payment import (
    PaymentConfirmSchema,
    PaymentCreateSchema,
    PaymentSchema,
    PaymentStatusUpdateSchema,
    BillingConfirmSchema,
)

from datetime import timedelta

load_dotenv()

router = APIRouter()


TOSS_CONFIRM_URL = "https://api.tosspayments.com/v1/payments/confirm"
# 토스 취소 URL
TOSS_CANCEL_URL = "https://api.tosspayments.com/v1/payments/{}/cancel"


def ensure_payment_table():
    Payment.__table__.create(bind=engine, checkfirst=True)


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

    payment = Payment(
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
        db.query(Payment)
        .filter(Payment.toss_order_id == payment_confirm.order_id)
        .first()
    )

    if payment is None:
        payment = Payment(
            toss_order_id=payment_confirm.order_id,
            user_id=payment_confirm.user_id,
        )
        db.add(payment)

    payment.amount = toss_data.get("totalAmount", payment_confirm.amount)
    payment.payment_status = toss_data.get("status", "DONE")
    payment.payment_method = toss_data.get("method")
    payment.toss_payment_key = toss_data.get("paymentKey", payment_confirm.payment_key)
    payment.paid_at = parse_toss_datetime(toss_data.get("approvedAt"))

    user = db.query(User).filter(User.user_id == payment.user_id).first()
    if user:
        days = 90 if payment.amount == 9900 else 30
        base_date = datetime.now(timezone.utc).date()
        if user.subscription_end_date and user.subscription_end_date > base_date:
            base_date = user.subscription_end_date
        user.subscription_end_date = base_date + timedelta(days=days)

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

    query = db.query(Payment)

    if user_id is not None:
        query = query.filter(Payment.user_id == user_id)

    return (
        query.order_by(Payment.payment_id.desc())
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
        db.query(Payment)
        .filter(Payment.payment_id == payment_id)
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
        db.query(Payment)
        .filter(Payment.payment_id == payment_id)
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


# 추가 - 결제 취소 엔드포인트
@router.post("/cancel", status_code=status.HTTP_200_OK)
async def cancel_payment(
    payment_id: int,
    cancel_reason: str = "플랜 변경",
    db: Session = Depends(get_db),
):
    payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found.")
    if not payment.toss_payment_key:
        raise HTTPException(status_code=400, detail="토스 결제 키를 찾을 수 없습니다.")

    headers = {
        "Authorization": get_toss_authorization_header(),
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        toss_response = await client.post(
            TOSS_CANCEL_URL.format(payment.toss_payment_key),
            headers=headers,
            json={"cancelReason": cancel_reason},
        )

    if toss_response.status_code >= 400:
        raise HTTPException(status_code=toss_response.status_code, detail=toss_response.json())

    payment.payment_status = "CANCELLED"

    user = db.query(User).filter(User.user_id == payment.user_id).first()
    if user:
        user.subscription_end_date = None

    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to cancel payment.") from error

    return {"message": "결제가 취소되었습니다."}


# 토스 빌링키 발급 API URL
TOSS_BILLING_ISSUE_URL = "https://api.tosspayments.com/v1/billing/authorizations/issue"
# 토스 빌링 승인 API URL (뒤에 billingKey 붙음)
TOSS_BILLING_CHARGE_URL = "https://api.tosspayments.com/v1/billing/{}"


@router.post(
    "/billing/confirm",
    response_model=PaymentSchema,
    status_code=status.HTTP_200_OK,
)
async def confirm_billing(
    billing_confirm: BillingConfirmSchema,
    db: Session = Depends(get_db),
):
    ensure_payment_table()

    headers = {
        "Authorization": get_toss_authorization_header(),
        "Content-Type": "application/json",
    }
    
    # 1. 토스 빌링키 발급 API 호출
    issue_payload = {
        "authKey": billing_confirm.auth_key,
        "customerKey": billing_confirm.customer_key,
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        issue_response = await client.post(TOSS_BILLING_ISSUE_URL, headers=headers, json=issue_payload)
    
    issue_data = issue_response.json()
    if issue_response.status_code >= 400:
        raise HTTPException(
            status_code=issue_response.status_code,
            detail=issue_data,
        )
    
    billing_key = issue_data.get("billingKey")
    if not billing_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve billing key from Toss Payments.",
        )
        
    # 2. 유저 정보 조회 및 빌링키 저장
    user = db.query(User).filter(User.user_id == billing_confirm.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
        
    user.billing_key = billing_key
    user.customer_key = billing_confirm.customer_key
    
    # 3. 자동결제 승인 API 호출 (첫 달 결제)
    order_id = f"billing_{uuid.uuid4().hex[:20]}"
    charge_payload = {
        "customerKey": billing_confirm.customer_key,
        "amount": billing_confirm.amount,
        "orderId": order_id,
        "orderName": "WITH 스탠다드 정기 결제",
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        charge_response = await client.post(
            TOSS_BILLING_CHARGE_URL.format(billing_key),
            headers=headers,
            json=charge_payload,
        )
        
    charge_data = charge_response.json()
    if charge_response.status_code >= 400:
        # 빌링키는 발급되었으나 첫 결제가 실패한 경우, 빌링키 롤백
        user.billing_key = None
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
        raise HTTPException(
            status_code=charge_response.status_code,
            detail=charge_data,
        )
        
    # 4. 결제 데이터 기록 생성
    payment = Payment(
        amount=charge_data.get("totalAmount", billing_confirm.amount),
        payment_status=charge_data.get("status", "DONE"),
        payment_method="CARD",
        toss_order_id=order_id,
        toss_payment_key=charge_data.get("paymentKey"),
        paid_at=parse_toss_datetime(charge_data.get("approvedAt")),
        user_id=billing_confirm.user_id,
    )
    db.add(payment)
    
    # 5. 멤버십 만료일 업데이트 (30일 추가)
    base_date = datetime.now(timezone.utc).date()
    if user.subscription_end_date and user.subscription_end_date > base_date:
        base_date = user.subscription_end_date
    user.subscription_end_date = base_date + timedelta(days=30)
    
    try:
        db.commit()
        db.refresh(payment)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save payment information.",
        ) from error
        
    return payment


@router.post("/billing/stop-recurring", status_code=status.HTTP_200_OK)
def stop_recurring_billing(
    user_id: int,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    user.billing_key = None
    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to stop recurring billing.") from error
        
    return {"message": "정기 결제가 해지되었습니다. 만료일까지만 이용 가능합니다."}


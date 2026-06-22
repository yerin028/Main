import base64
import os
import uuid
from datetime import datetime, timedelta, timezone
import httpx
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import database, models
from app.core.mysql_database import get_db, SessionLocal
from app.models.users import User
from app.models.payment import Payment

load_dotenv()

TOSS_BILLING_CHARGE_URL = "https://api.tosspayments.com/v1/billing/{}"

def get_toss_authorization_header():
    toss_secret_key = os.getenv("TOSS_SECRET_KEY")
    if not toss_secret_key:
        print("Error: TOSS_SECRET_KEY is not configured.")
        return None
    encoded_key = base64.b64encode(f"{toss_secret_key}:".encode("utf-8")).decode("utf-8")
    return f"Basic {encoded_key}"

def parse_toss_datetime(date_text: str | None):
    if not date_text:
        return None
    return datetime.fromisoformat(date_text.replace("Z", "+00:00"))

def run_recurring_billing():
    print(f"[{datetime.now()}] Starting automatic billing renewal cron job...")
    
    auth_header = get_toss_authorization_header()
    if not auth_header:
        return

    db = SessionLocal()
    try:
        # 1. 만료일이 오늘 이하(과거 또는 오늘)이고, 빌링키가 있는 유저 조회
        today = datetime.now(timezone.utc).date()
        users_to_bill = db.query(User).filter(
            User.billing_key.isnot(None),
            User.subscription_end_date <= today
        ).all()
        
        print(f"Found {len(users_to_bill)} users to renew.")
        
        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json",
        }
        
        for user in users_to_bill:
            print(f"Processing renewal for User ID: {user.user_id} ({user.name})")
            
            # 기본 정기 구독 금액 (기본 스탠다드 요금제 4900원)
            amount = 4900
            order_id = f"billing_{uuid.uuid4().hex[:20]}"
            
            payload = {
                "customerKey": user.customer_key,
                "amount": amount,
                "orderId": order_id,
                "orderName": "WITH 스탠다드 정기 결제 (자동 갱신)",
            }
            
            try:
                # 2. 토스 자동결제 승인 API 호출
                response = httpx.post(
                    TOSS_BILLING_CHARGE_URL.format(user.billing_key),
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                
                charge_data = response.json()
                if response.status_code >= 400:
                    print(f"Payment failed for user {user.user_id}: {charge_data}")
                    # 결제 실패 시 자동결제를 해지하거나 로그를 남깁니다.
                    # 여기서는 안전하게 빌링키를 제거하여 다음 날 중복 시도를 막고 구독을 중단합니다.
                    user.billing_key = None
                    db.commit()
                    continue
                
                # 3. 결제 데이터 기록 생성
                payment = Payment(
                    amount=charge_data.get("totalAmount", amount),
                    payment_status=charge_data.get("status", "DONE"),
                    payment_method="CARD",
                    toss_order_id=order_id,
                    toss_payment_key=charge_data.get("paymentKey"),
                    paid_at=parse_toss_datetime(charge_data.get("approvedAt")),
                    user_id=user.user_id,
                )
                db.add(payment)
                
                # 4. 멤버십 만료일 업데이트 (기존 만료일에 30일 추가)
                base_date = user.subscription_end_date if user.subscription_end_date else today
                user.subscription_end_date = base_date + timedelta(days=30)
                
                db.commit()
                print(f"Successfully renewed User ID: {user.user_id}. New expiration: {user.subscription_end_date}")
                
            except Exception as e:
                db.rollback()
                print(f"Error processing user {user.user_id}: {e}")
                
    finally:
        db.close()
        print("Renewal cron job finished.")

if __name__ == "__main__":
    run_recurring_billing()

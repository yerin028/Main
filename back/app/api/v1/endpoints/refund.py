from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import PyMongoError
from sqlalchemy.orm import Session

from app.core.mongo_database import get_mongo_collection
from app.core.mysql_database import get_db
from app.models.cs import REFUND_COLLECTION
from app.models.payment import Payment
from app.models.users import User
from app.schemas.cs import RefundCreate, RefundSchema

router = APIRouter()


def get_refund_collection():
    return get_mongo_collection(REFUND_COLLECTION)


def next_sequence(collection, sequence_field: str):
    latest_document = collection.find_one(sort=[(sequence_field, -1)])
    if not latest_document:
        return 1

    return int(latest_document.get(sequence_field, 0)) + 1


def get_user_snapshot(db: Session, user_id: int | None):
    if user_id is None:
        return {}

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return {
        "user_id": user.user_id,
        "user_name": user.name,
        "user_email": user.email,
    }


def get_payment_snapshot(db: Session, payment_id: int | None):
    if payment_id is None:
        return {}

    payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    return {
        "payment_id": payment.payment_id,
        "payment_amount": payment.amount,
        "payment_status": payment.payment_status,
        "toss_order_id": payment.toss_order_id,
        "payment_user_id": payment.user_id,
    }


def serialize_refund(document):
    return RefundSchema(
        refund_id=document["refund_id"],
        reason=document.get("reason"),
        status=document.get("status"),
        request_at=document.get("request_at"),
        processed_at=document.get("processed_at"),
        payment_id=document.get("payment_id"),
        user_id=document.get("user_id"),
        user_name=document.get("user_name"),
        user_email=document.get("user_email"),
        payment_amount=document.get("payment_amount"),
        payment_status=document.get("payment_status"),
        toss_order_id=document.get("toss_order_id"),
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
    collection = get_refund_collection()
    payment_snapshot = get_payment_snapshot(db, refund_create.payment_id)
    user_id = refund_create.user_id or payment_snapshot.get("payment_user_id")
    user_snapshot = get_user_snapshot(db, user_id)

    try:
        document = {
            "refund_id": next_sequence(collection, "refund_id"),
            "reason": refund_create.reason,
            "status": "신청",
            "request_at": datetime.now(timezone.utc),
            "processed_at": None,
            **payment_snapshot,
            **user_snapshot,
        }
        document.pop("payment_user_id", None)
        collection.insert_one(document)
    except PyMongoError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create refund: {error}",
        ) from error

    return serialize_refund(document)

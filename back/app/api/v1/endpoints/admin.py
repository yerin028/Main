from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.errors import PyMongoError
from sqlalchemy.orm import Session

from app.core.mongo_database import get_mongo_collection
from app.core.mysql_database import get_db
from app.models.cs import REFUND_COLLECTION
from app.models.payment import Payment
from app.models.users import User
from app.schemas.cs import RefundSchema, RefundStatusUpdate
from app.schemas.payment import PaymentSchema

router = APIRouter()


def get_refund_collection():
    return get_mongo_collection(REFUND_COLLECTION)


def get_optional_user_snapshot(db: Session | None, user_id: int | None):
    if db is None or user_id is None:
        return {}

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return {"user_id": user_id}

    return {
        "user_id": user.user_id,
        "user_name": user.name,
        "user_email": user.email,
    }


def get_payment_user_id(db: Session | None, payment_id: int | None):
    if db is None or payment_id is None:
        return None

    payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    if not payment:
        return None

    return payment.user_id


def get_refund_user_snapshot(document, db: Session | None = None):
    user_id = document.get("user_id") or get_payment_user_id(db, document.get("payment_id"))
    user_snapshot = {
        "user_id": user_id,
        "user_name": document.get("user_name"),
        "user_email": document.get("user_email"),
    }

    if user_id and not (user_snapshot["user_name"] or user_snapshot["user_email"]):
        user_snapshot.update(get_optional_user_snapshot(db, user_id))

    return user_snapshot


def serialize_refund(document, db: Session | None = None):
    user_snapshot = get_refund_user_snapshot(document, db)

    return RefundSchema(
        refund_id=document["refund_id"],
        reason=document.get("reason"),
        status=document.get("status"),
        request_at=document.get("request_at"),
        processed_at=document.get("processed_at"),
        payment_id=document.get("payment_id"),
        user_id=user_snapshot.get("user_id"),
        user_name=user_snapshot.get("user_name"),
        user_email=user_snapshot.get("user_email"),
        payment_amount=document.get("payment_amount"),
        payment_status=document.get("payment_status"),
        toss_order_id=document.get("toss_order_id"),
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
    try:
        documents = get_refund_collection().find({}).sort("refund_id", 1)
        return [serialize_refund(document, db) for document in documents]
    except PyMongoError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read refunds: {error}",
        ) from error


@router.put(
    "/refunds",
    response_model=RefundSchema,
    status_code=status.HTTP_200_OK,
)
def update_admin_refund(refund_update: RefundStatusUpdate, db: Session = Depends(get_db)):
    if refund_update.status not in {"승인됨", "거절됨"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund status must be 승인됨 or 거절됨.",
        )

    try:
        collection = get_refund_collection()
        refund = collection.find_one({"refund_id": refund_update.refund_id})

        if not refund:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Refund not found.",
            )

        if refund.get("status") in {"승인됨", "거절됨"}:
            return serialize_refund(refund, db)

        collection.update_one(
            {"refund_id": refund_update.refund_id},
            {"$set": {"status": refund_update.status}},
        )
        updated_refund = collection.find_one({"refund_id": refund_update.refund_id})
    except PyMongoError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update refund: {error}",
        ) from error

    return serialize_refund(updated_refund, db)

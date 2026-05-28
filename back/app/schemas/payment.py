from datetime import datetime
from pydantic import BaseModel, Field


class PaymentBase(BaseModel):
    amount: int
    payment_status: str
    payment_method: str | None = None
    toss_order_id: str | None = None
    paid_at: datetime | None = None
    toss_payment_key: str | None = None
    user_id: int


class PaymentCreate(PaymentBase):
    pass


class PaymentSchema(PaymentBase):
    payment_id: int

    class Config:
        from_attributes = True

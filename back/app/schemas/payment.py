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


class PaymentStatusUpdate(BaseModel):
    payment_status: str = Field(..., max_length=50)
    payment_method: str | None = Field(default=None, max_length=50)
    paid_at: datetime | None = None


class PaymentConfirm(BaseModel):
    payment_key: str = Field(..., max_length=200)
    order_id: str = Field(..., max_length=100)
    amount: int = Field(..., ge=0)
    user_id: int


class PaymentSchema(PaymentBase):
    payment_id: int

    class Config:
        from_attributes = True


class BillingConfirmSchema(BaseModel):
    auth_key: str
    customer_key: str
    amount: int
    user_id: int


PaymentCreateSchema = PaymentCreate
PaymentStatusUpdateSchema = PaymentStatusUpdate
PaymentConfirmSchema = PaymentConfirm


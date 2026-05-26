from datetime import datetime

from pydantic import BaseModel, Field


class PaymentCreateSchema(BaseModel):
    amount: int = Field(..., ge=0, description="Payment amount.")
    payment_status: str = Field(default="READY", max_length=50, description="Payment status.")
    payment_method: str | None = Field(default=None, max_length=100, description="Payment method.")
    toss_order_id: str | None = Field(default=None, max_length=255, description="Toss order id.")
    user_id: int | None = Field(default=None, description="User id.")


class PaymentStatusUpdateSchema(BaseModel):
    payment_status: str = Field(..., max_length=50, description="Changed payment status.")
    payment_method: str | None = Field(default=None, max_length=100, description="Payment method.")
    paid_at: datetime | None = Field(default=None, description="Paid datetime.")


class PaymentConfirmSchema(BaseModel):
    payment_key: str = Field(..., max_length=200, description="Toss payment key.")
    order_id: str = Field(..., max_length=64, description="Toss order id.")
    amount: int = Field(..., ge=0, description="Payment amount.")
    user_id: int | None = Field(default=None, description="User id.")


class PaymentSchema(BaseModel):
    payment_id: int
    amount: int
    payment_status: str
    payment_method: str | None = None
    toss_order_id: str | None = None
    payment_key: str | None = None
    paid_at: datetime | None = None
    user_id: int | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}

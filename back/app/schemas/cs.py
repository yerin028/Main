from datetime import datetime

from pydantic import BaseModel, Field


class CSQuestionCreate(BaseModel):
    content: str = Field(..., description="Question content.")
    user_id: int | None = Field(default=None, description="Question writer user id.")


class CSAnswerCreate(BaseModel):
    question_id: int = Field(..., description="Question id to answer.")
    content: str = Field(..., description="Answer content.")
    user_id: int | None = Field(default=None, description="Admin user id.")


class CSAnswerSchema(BaseModel):
    answer_id: int
    content: str
    created_at: datetime | str | None = None
    user_id: int | None = None
    user_name: str | None = None
    user_email: str | None = None
    question_id: int | None = None

    class Config:
        from_attributes = True


class CSQuestionSchema(BaseModel):
    question_id: int
    content: str
    created_at: datetime | str | None = None
    user_id: int | None = None
    user_name: str | None = None
    user_email: str | None = None
    answer_status: str
    answers: list[CSAnswerSchema] = Field(default_factory=list)

    class Config:
        from_attributes = True


class RefundCreate(BaseModel):
    reason: str | None = Field(default=None, description="Refund reason.")
    payment_id: int | None = Field(default=None, description="Payment id.")
    user_id: int | None = Field(default=None, description="Refund requester user id.")


class RefundSchema(BaseModel):
    refund_id: int
    reason: str | None = None
    status: str | None = None
    request_at: datetime | str | None = None
    processed_at: datetime | str | None = None
    payment_id: int | None = None
    user_id: int | None = None
    user_name: str | None = None
    user_email: str | None = None
    payment_amount: int | None = None
    payment_status: str | None = None
    toss_order_id: str | None = None
    toss_payment_key: str | None = None 

    class Config:
        from_attributes = True


class RefundStatusUpdate(BaseModel):
    refund_id: int
    status: str

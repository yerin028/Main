from datetime import datetime

from pydantic import BaseModel, Field


class CSQuestionCreate(BaseModel):
    content: str = Field(..., description="Question content.")
    user_id: int | None = Field(default=None, description="Question writer user id.")


class CSQuestionSchema(BaseModel):
    question_id: int
    content: str
    created_at: datetime | None = None
    user_id: int | None = None
    answer_status: str

    class Config:
        from_attributes = True


class CSAnswerCreate(BaseModel):
    question_id: int = Field(..., description="Question id to answer.")
    content: str = Field(..., description="Answer content.")
    user_id: int | None = Field(default=None, description="Admin user id.")


class CSAnswerSchema(BaseModel):
    answer_id: int
    content: str
    created_at: datetime | None = None
    user_id: int | None = None
    question_id: int | None = None

    class Config:
        from_attributes = True


class RefundCreate(BaseModel):
    reason: str | None = Field(default=None, description="Refund reason.")
    payment_id: int | None = Field(default=None, description="Payment id.")


class RefundSchema(BaseModel):
    refund_id: int
    reason: str | None = None
    status: str | None = None
    request_at: datetime | None = None
    processed_at: datetime | None = None
    payment_id: int | None = None

    class Config:
        from_attributes = True

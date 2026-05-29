from datetime import datetime
from pydantic import BaseModel, Field


class UserBase(BaseModel):
    email: str | None = Field(default=None, description="User email.")
    social_provider: str | None = Field(default=None, description="Social provider (kakao, google, naver).")
    social_id: str | None = Field(default=None, description="Social login unique ID.")
    name: str | None = Field(default=None, description="User real name or nickname.")
    role: str | None = Field(default="user", description="User role.")
    subscription_end_date: datetime | None = Field(default=None, description="Subscription expiration date.")
    customer_key: str | None = Field(default=None, description="Toss Payments customer key.")
    billing_key: str | None = Field(default=None, description="Toss Payments billing key.")


class UserCreate(UserBase):
    password: str | None = Field(default=None, description="User password (hashed).")


class UserUpdate(UserBase):
    password: str | None = Field(default=None, description="User password (optional update).")


class UserSchema(UserBase):
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

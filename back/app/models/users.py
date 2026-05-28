from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.mysql_database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(100), unique=True, index=True, nullable=True)
    password = Column(String(255), nullable=True)
    social_provider = Column(String(50), nullable=True)  # kakao, google, naver
    social_id = Column(String(100), nullable=True)
    name = Column(String(100), nullable=True)
    role = Column(String(20), default="user", nullable=True)
    subscription_end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    customer_key = Column(String(100), nullable=True)
    billing_key = Column(String(100), nullable=True)

    # Relationships
    payments = relationship("Payment", back_populates="user")
    # quiz_results = relationship("QuizResult", back_populates="user") # Uncomment if QuizResult model exists

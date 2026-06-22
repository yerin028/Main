from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.mysql_database import Base


class Payment(Base):
    __tablename__ = "Payment"

    payment_id = Column(Integer, primary_key=True, autoincrement=True)
    amount = Column(Integer, nullable=False)
    payment_status = Column(String(50), nullable=False)
    payment_method = Column(String(50), nullable=True)
    toss_order_id = Column(String(100), nullable=True)
    paid_at = Column(DateTime, nullable=True)
    toss_payment_key = Column(String(100), nullable=True)
    user_id = Column(Integer, ForeignKey("Users.user_id"), nullable=False)

    user = relationship("User", back_populates="payments")
    refunds = relationship("Refund", back_populates="payment")

class Refund(Base):
    __tablename__ = "Refund"

    refund_id    = Column(Integer, primary_key=True, autoincrement=True)
    reason       = Column(Text, nullable=True)
    status       = Column(String(50), nullable=False, default="신청")
    request_at   = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    payment_id   = Column(Integer, ForeignKey("Payment.payment_id"), nullable=True)

    payment = relationship("Payment", back_populates="refunds")
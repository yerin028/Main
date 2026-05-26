from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.core.mysql_database import Base


class PaymentModel(Base):
    __tablename__ = "Payment"

    payment_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    amount = Column(Integer, nullable=False)
    payment_status = Column(String(50), nullable=False)
    payment_method = Column(String(100), nullable=True)
    toss_order_id = Column(String(255), nullable=True)
    payment_key = Column(String(255), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

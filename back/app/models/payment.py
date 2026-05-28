from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

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

    # Relationships
    user = relationship("User", back_populates="payments")

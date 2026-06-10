from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Computed
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.mysql_database import Base

class UserWithdrawal(Base):
    __tablename__ = "UserWithdrawals"

    withdrawal_id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id               = Column(Integer, ForeignKey("Users.user_id"), nullable=False)
    email                 = Column(String(255), nullable=True)
    password              = Column(String(255), nullable=True)
    social_provider       = Column(String(50), nullable=True)
    social_id             = Column(String(255), nullable=True)
    name                  = Column(String(100), nullable=True)
    role                  = Column(String(20), nullable=True)
    customer_key          = Column(String(100), nullable=True)
    billing_key           = Column(String(100), nullable=True)
    subscription_end_date = Column(Date, nullable=True)
    created_at            = Column(DateTime, nullable=True)
    deleted_at            = Column(DateTime(timezone=True), server_default=func.now())
    deleted_after         = Column(DateTime, Computed("deleted_at + INTERVAL 30 DAY", persisted=True))

    user = relationship("User", back_populates="withdrawal")
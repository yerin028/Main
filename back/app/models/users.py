from sqlalchemy import Column, Integer, String, Date, DateTime
from sqlalchemy.sql import func
from app.core.mysql_database import Base

class UsersModel(Base):
    __tablename__="Users"

    user_id               = Column(Integer, primary_key=True, autoincrement=True)
    email                 = Column(String(255), nullable=True)
    password              = Column(String(255), nullable=True)
    social_provider       = Column(String(50), nullable=True)
    social_id             = Column(String(255), nullable=True)
    name                  = Column(String(100), nullable=True)
    role                  = Column(String(20), default='user')
    customer_key          = Column(String(100), nullable=True, unique=True)
    billing_key           = Column(String(100), nullable=True)
    subscription_end_date = Column(Date, nullable=True)
    created_at            = Column(DateTime, server_default=func.now())
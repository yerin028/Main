from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.mysql_database import Base


class CSQuestion(Base):
    __tablename__ = "CS_Question"

    question_id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    user_id = Column(Integer, ForeignKey("Users.user_id"), nullable=True)

    answers = relationship("CSAnswer", back_populates="question")


class CSAnswer(Base):
    __tablename__ = "CS_Answer"

    answer_id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    user_id = Column(Integer, ForeignKey("Users.user_id"), nullable=True)
    question_id = Column(Integer, ForeignKey("CS_Question.question_id"), nullable=True)

    question = relationship("CSQuestion", back_populates="answers")


class Refund(Base):
    __tablename__ = "Refund"

    refund_id = Column(Integer, primary_key=True, autoincrement=True)
    reason = Column(Text, nullable=True)
    status = Column(String(50), nullable=True, default="신청")
    request_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    payment_id = Column(Integer, ForeignKey("Payment.payment_id"), nullable=True)

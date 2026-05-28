from sqlalchemy import Column, Integer, Text, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.mysql_database import Base


class Quiz(Base):
    __tablename__ = "quizzes"

    quiz_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    quiz_type = Column(String(50), nullable=True)
    lesson_id = Column(Integer, ForeignKey("lessons.lesson_id"), nullable=False)

    # Relationships
    lesson = relationship("Lesson")
    results = relationship("QuizResult", back_populates="quiz")


class QuizResult(Base):
    __tablename__ = "quiz_results"

    result_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    is_correct = Column(Boolean, nullable=True)
    answered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.quiz_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)

    # Relationships
    quiz = relationship("Quiz", back_populates="results")
    user = relationship("User")

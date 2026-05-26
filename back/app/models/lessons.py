from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.mysql_database import Base


class LessonCategory(Base):
    __tablename__ = "lesson_categories"

    category_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    lessons = relationship("Lesson", back_populates="category")


class Lesson(Base):
    __tablename__ = "lessons"

    lesson_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("lesson_categories.category_id"), nullable=False)
    word = Column(String(100), nullable=False)
    video_url = Column(String(500), nullable=True)
    video_type = Column(String(30), nullable=False, default="placeholder")
    description = Column(Text, nullable=True)
    ai_model_key = Column(String(100), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    category = relationship("LessonCategory", back_populates="lessons")

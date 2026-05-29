from datetime import datetime

from pydantic import BaseModel, Field


class QuizCategorySchema(BaseModel):
    category_id: int = Field(..., description="Quiz category id used by frontend.")
    name: str = Field(..., description="Quiz category name.")
    icon: str | None = Field(default=None, description="Frontend icon key.")
    description: str | None = Field(default=None, description="Category helper text.")
    sort_order: int = Field(default=0, description="Display order.")


class QuizSchema(BaseModel):
    quiz_id: int
    question: str
    answer: str
    quiz_type: str | None = None
    lesson_id: int | None = None
    lesson_id2: int | None = None
    category_id: int | None = None
    category_name: str | None = None
    video_url: str | None = None
    options: list[str] = Field(default_factory=list)
    description: str | None = None
    sort_order: int = 0


class QuizResultCreateSchema(BaseModel):
    quiz_id: int = Field(..., description="Solved quiz id.")
    selected_option: str | None = Field(default=None, description="User selected answer.")
    is_correct: bool = Field(..., description="Whether selected answer was correct.")
    user_id: int | None = Field(default=None, description="User id.")


class QuizResultSchema(BaseModel):
    result_id: int
    is_correct: bool
    answered_at: datetime
    user_id: int | None = None
    quiz_id: int
    selected_option: str | None = None

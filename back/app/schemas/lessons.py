from pydantic import BaseModel, Field


class LessonCategorySchema(BaseModel):
    category_id: int = Field(..., description="Learning category id.")
    name: str = Field(..., description="Category display name.")
    description: str | None = Field(default=None, description="Category helper text.")
    sort_order: int = Field(default=0, description="Display order.")


class LessonSummarySchema(BaseModel):
    lesson_id: int = Field(..., description="Lesson id.")
    category_id: int = Field(..., description="Parent category id.")
    word: str = Field(..., description="Sign language word.")
    sort_order: int = Field(default=0, description="Display order in category.")


class LessonDetailSchema(LessonSummarySchema):
    category_name: str = Field(..., description="Parent category name.")
    video_url: str | None = Field(
        default=None,
        description="Sign language lesson video URL. Can be replaced by uploaded AI video later.",
    )
    video_type: str = Field(
        default="placeholder",
        description="video, stream, ai-generated, or placeholder.",
    )
    description: str | None = Field(
        default=None,
        description="Current lesson explanation. AI generated text can be stored here later.",
    )
    ai_model_key: str | None = Field(
        default=None,
        description="Future AI model or prompt key used to generate this lesson.",
    )


class LessonListResponseSchema(BaseModel):
    categories: list[LessonCategorySchema]
    lessons: list[LessonSummarySchema]
    selected_category_id: int | None = None
    page: int = 1
    size: int
    total: int


class LessonProgressSaveSchema(BaseModel):
    user_id: int = Field(..., description="Learning user id.")
    category_id: int = Field(..., description="Learning category id.")
    lesson_id: int = Field(..., description="Last studied lesson id.")
    lesson_index: int = Field(default=0, description="Zero-based lesson position in category.")
    word: str | None = Field(default=None, description="Last studied word.")


class LessonProgressSchema(LessonProgressSaveSchema):
    category_name: str | None = Field(default=None, description="Learning category display name.")
    updated_at: str | None = Field(default=None, description="Last progress save time.")

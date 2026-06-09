from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LessonCategoryDocument(BaseModel):
    # MongoDB lesson_categories 컬렉션에 저장되는 카테고리 문서 구조입니다.
    category_id: int = Field(..., description="Learning category id.")
    name: str = Field(..., description="Category display name.")
    description: str | None = Field(default=None, description="Category helper text.")
    sort_order: int = Field(default=0, description="Display order.")
    created_at: datetime | None = Field(default=None, description="Document creation time.")
    updated_at: datetime | None = Field(default=None, description="Document update time.")


class LessonDocument(BaseModel):
    # MongoDB lessons 컬렉션에 저장되는 수어학습 문서 구조입니다.
    lesson_id: int = Field(..., description="Lesson id.")
    category_id: int = Field(..., description="Parent category id.")
    word: str = Field(..., description="Sign language word.")
    video_url: str | None = Field(default=None, description="Sign language lesson video URL.")
    video_type: str = Field(default="placeholder", description="Lesson video type.")
    description: str | None = Field(default=None, description="Lesson explanation.")
    ai_model_key: str | None = Field(default=None, description="Future AI model or prompt key.")
    sort_order: int = Field(default=0, description="Display order in category.")
    source: str | None = Field(default=None, description="Data source, such as sign_api.")
    api_keyword: str | None = Field(default=None, description="Keyword used for source API sync.")
    synced_at: datetime | None = Field(default=None, description="External API sync time.")
    created_at: datetime | None = Field(default=None, description="Document creation time.")
    updated_at: datetime | None = Field(default=None, description="Document update time.")


def to_mongo_document(model: BaseModel) -> dict[str, Any]:
    # None 값은 MongoDB에 굳이 저장하지 않도록 제외합니다.
    return model.model_dump(exclude_none=True)

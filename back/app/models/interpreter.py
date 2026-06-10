from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class InterpreterLogDocument(BaseModel):
    # MongoDB interpreter_log 컬렉션에 저장되는 통역 기록 문서 구조입니다.
    input_type: str = Field(default="camera", description="Translation input type.")
    result_text: str = Field(..., description="Recognized Korean text.")
    korean_text: str = Field(..., description="Recognized Korean text.")
    english_text: str = Field(..., description="Translated English text.")
    confidence: float = Field(..., description="Recognition confidence from 0.0 to 1.0.")
    language_from: str = Field(default="ko", description="Source language code.")
    language_to: str = Field(default="en", description="Target language code.")
    user_id: int | None = Field(default=None, description="Optional logged-in user id.")
    created_at: datetime | None = Field(default=None, description="Document creation time.")


def to_mongo_document(model: BaseModel) -> dict[str, Any]:
    # None 값은 MongoDB에 굳이 저장하지 않도록 제외합니다.
    return model.model_dump(exclude_none=True)

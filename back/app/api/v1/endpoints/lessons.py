from fastapi import APIRouter, HTTPException, Query, status
from pymongo import ASCENDING
from pymongo.errors import PyMongoError

from app.core.mongo_database import (
    get_lesson_categories_collection,
    get_lessons_collection,
)
from app.schemas.lessons import (
    LessonCategorySchema,
    LessonDetailSchema,
    LessonListResponseSchema,
    LessonSummarySchema,
)

router = APIRouter()


DEFAULT_LESSON_CATEGORIES = [
    {"category_id": 1, "name": "인사", "description": "인사 표현을 학습합니다.", "sort_order": 1},
    {"category_id": 2, "name": "일상생활", "description": "일상생활 표현을 학습합니다.", "sort_order": 2},
    {"category_id": 3, "name": "가족", "description": "가족 관련 표현을 학습합니다.", "sort_order": 3},
    {"category_id": 4, "name": "학교/직장", "description": "학교와 직장 표현을 학습합니다.", "sort_order": 4},
    {"category_id": 5, "name": "교통/장소", "description": "교통과 장소 표현을 학습합니다.", "sort_order": 5},
    {"category_id": 6, "name": "시간/날짜", "description": "시간과 날짜 표현을 학습합니다.", "sort_order": 6},
    {"category_id": 7, "name": "감정/상태", "description": "감정과 상태 표현을 학습합니다.", "sort_order": 7},
    {"category_id": 8, "name": "기타", "description": "기타 표현을 학습합니다.", "sort_order": 8},
]


DEFAULT_LESSONS = [
    {
        "lesson_id": 101,
        "category_id": 1,
        "word": "동생",
        "video_url": None,
        "video_type": "placeholder",
        "description": "단어의 의미",
        "ai_model_key": None,
        "sort_order": 1,
    },
    {
        "lesson_id": 102,
        "category_id": 1,
        "word": "안녕하세요",
        "video_url": None,
        "video_type": "placeholder",
        "description": "인사할 때 사용하는 표현입니다.",
        "ai_model_key": None,
        "sort_order": 2,
    },
    *[
        {
            "lesson_id": category_id * 100 + 1,
            "category_id": category_id,
            "word": "동생",
            "video_url": None,
            "video_type": "placeholder",
            "description": "단어의 의미",
            "ai_model_key": None,
            "sort_order": 1,
        }
        for category_id in range(2, 9)
    ],
]


def ensure_default_lesson_data():
    # MongoDB 컬렉션이 비어 있으면 기존 임시 데이터를 초기 데이터로 저장합니다.
    # 이미 같은 ID가 있으면 덮어쓰지 않아 DB에서 수정한 값을 보존합니다.
    category_collection = get_lesson_categories_collection()
    lesson_collection = get_lessons_collection()

    for category in DEFAULT_LESSON_CATEGORIES:
        category_collection.update_one(
            {"category_id": category["category_id"]},
            {"$setOnInsert": category},
            upsert=True,
        )

    for lesson in DEFAULT_LESSONS:
        lesson_collection.update_one(
            {"lesson_id": lesson["lesson_id"]},
            {"$setOnInsert": lesson},
            upsert=True,
        )

    return category_collection, lesson_collection


def to_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def convert_category_document(document) -> dict:
    return {
        "category_id": to_int(document.get("category_id")),
        "name": document.get("name", ""),
        "description": document.get("description"),
        "sort_order": to_int(document.get("sort_order")),
    }


def convert_lesson_summary_document(document) -> dict:
    return {
        "lesson_id": to_int(document.get("lesson_id")),
        "category_id": to_int(document.get("category_id")),
        "word": document.get("word", ""),
        "sort_order": to_int(document.get("sort_order")),
    }


def convert_lesson_detail_document(document, category: dict) -> dict:
    return {
        **convert_lesson_summary_document(document),
        "category_name": category.get("name", ""),
        "video_url": document.get("video_url"),
        "video_type": document.get("video_type") or "placeholder",
        "description": document.get("description"),
        "ai_model_key": document.get("ai_model_key"),
    }


@router.get(
    "/categories",
    response_model=list[LessonCategorySchema],
    status_code=status.HTTP_200_OK,
)
async def read_lesson_categories():
    try:
        category_collection, _ = ensure_default_lesson_data()
        categories = category_collection.find({}).sort("sort_order", ASCENDING)
        return [convert_category_document(category) for category in categories]
    except PyMongoError as error:
        raise HTTPException(status_code=500, detail=f"Lesson MongoDB read failed: {error}")


@router.get(
    "",
    response_model=LessonListResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def read_lessons(
    category_id: int | None = Query(default=None, description="Filter lessons by category id."),
    page: int = Query(default=1, ge=1, description="Lesson page number."),
    size: int = Query(default=20, ge=1, le=100, description="Lessons per page."),
):
    try:
        category_collection, lesson_collection = ensure_default_lesson_data()
        category_documents = list(category_collection.find({}).sort("sort_order", ASCENDING))
        categories = [convert_category_document(category) for category in category_documents]

        mongo_query = {}
        if category_id is not None:
            category = category_collection.find_one({"category_id": category_id})
            if category is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Lesson category not found.",
                )
            mongo_query["category_id"] = category_id

        total = lesson_collection.count_documents(mongo_query)
        start = (page - 1) * size
        lesson_documents = list(
            lesson_collection.find(mongo_query)
            .sort([("category_id", ASCENDING), ("sort_order", ASCENDING), ("lesson_id", ASCENDING)])
            .skip(start)
            .limit(size)
        )
    except HTTPException:
        raise
    except PyMongoError as error:
        raise HTTPException(status_code=500, detail=f"Lesson MongoDB read failed: {error}")

    return LessonListResponseSchema(
        categories=categories,
        lessons=[
            LessonSummarySchema(**convert_lesson_summary_document(lesson))
            for lesson in lesson_documents
        ],
        selected_category_id=category_id,
        page=page,
        size=size,
        total=total,
    )


@router.get(
    "/{lesson_id}",
    response_model=LessonDetailSchema,
    status_code=status.HTTP_200_OK,
)
async def read_lesson_detail(lesson_id: int):
    try:
        category_collection, lesson_collection = ensure_default_lesson_data()
        lesson = lesson_collection.find_one({"lesson_id": lesson_id})
        if lesson is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found.",
            )

        category = category_collection.find_one({"category_id": to_int(lesson.get("category_id"))})
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson category not found.",
            )
    except HTTPException:
        raise
    except PyMongoError as error:
        raise HTTPException(status_code=500, detail=f"Lesson MongoDB read failed: {error}")

    return LessonDetailSchema(**convert_lesson_detail_document(lesson, category))

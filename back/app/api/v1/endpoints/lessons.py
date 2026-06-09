from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from pymongo import ASCENDING
from pymongo.errors import PyMongoError

from app.core.mongo_database import (
    get_dictionary_collection,
    get_lesson_categories_collection,
    get_lessons_collection,
    get_mongo_collection,
)
from app.schemas.lessons import (
    LessonCategorySchema,
    LessonDetailSchema,
    LessonListResponseSchema,
    LessonProgressSaveSchema,
    LessonProgressSchema,
    LessonSummarySchema,
)

router = APIRouter()

LESSON_PROGRESS_COLLECTION = "lesson_progress"


DEFAULT_LESSON_CATEGORIES = [
    {"category_id": 1, "name": "사회생활", "description": "사회생활 표현을 학습합니다.", "sort_order": 1},
    {"category_id": 2, "name": "일상생활", "description": "일상생활 표현을 학습합니다.", "sort_order": 2},
    {"category_id": 3, "name": "삶/가족", "description": "삶과 가족 관련 표현을 학습합니다.", "sort_order": 3},
    {"category_id": 4, "name": "교육/정보", "description": "교육과 정보통신 표현을 학습합니다.", "sort_order": 4},
    {"category_id": 5, "name": "교통/지역", "description": "교통과 지역 표현을 학습합니다.", "sort_order": 5},
    {"category_id": 6, "name": "개념/자연", "description": "개념과 자연 표현을 학습합니다.", "sort_order": 6},
    {"category_id": 7, "name": "인간/감정", "description": "인간과 감정 표현을 학습합니다.", "sort_order": 7},
    {"category_id": 8, "name": "기타/문화", "description": "기타와 문화 표현을 학습합니다.", "sort_order": 8},
]


LESSON_CATEGORY_SOURCE_MAP = {
    1: ["사회생활"],
    2: ["경제생활", "식생활", "의생활", "주생활", "의학"],
    3: ["삶"],
    4: ["교육", "정보통신"],
    5: ["교통", "나라명 및 지명"],
    6: ["개념", "자연"],
    7: ["인간"],
    8: ["기타", "문화"],
}


def ensure_default_lesson_data():
    # 카테고리 컬렉션만 기본값을 보정합니다.
    # lesson 영상 데이터는 국립수어원 API 호출 없이 MongoDB에 저장된 값만 사용합니다.
    category_collection = get_lesson_categories_collection()
    lesson_collection = get_lessons_collection()

    for category in DEFAULT_LESSON_CATEGORIES:
        category_collection.update_one(
            {"category_id": category["category_id"]},
            {"$set": category},
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


def get_document_lesson_id(document) -> int:
    for key in ("lesson_id", "dictionary_id", "local_id", "localId"):
        try:
            value = int(document.get(key))
            if value:
                return value
        except (TypeError, ValueError):
            continue
    return 0


def get_source_category(document) -> str:
    return str(document.get("category_name") or "").strip()


def get_category_id_from_source(document) -> int:
    source_category = get_source_category(document)
    for category_id, source_categories in LESSON_CATEGORY_SOURCE_MAP.items():
        if source_category in source_categories:
            return category_id
    return 0


def convert_lesson_summary_document(document, category_id: int | None = None) -> dict:
    return {
        "lesson_id": get_document_lesson_id(document),
        "category_id": category_id if category_id is not None else get_category_id_from_source(document),
        "word": document.get("word") or document.get("word_name", ""),
        "sort_order": to_int(document.get("sort_order")),
    }


def normalize_video_url(video_url: str | None) -> str | None:
    if not video_url:
        return None
    return video_url.replace("http://sldict.korean.go.kr", "https://sldict.korean.go.kr")


def convert_lesson_detail_document(document, category: dict) -> dict:
    return {
        **convert_lesson_summary_document(document, to_int(category.get("category_id"))),
        "category_name": category.get("name", ""),
        "video_url": normalize_video_url(document.get("video_url")),
        "video_type": document.get("video_type") or "placeholder",
        "description": document.get("description") or document.get("definition"),
        "ai_model_key": document.get("ai_model_key"),
    }


def is_valid_category_lesson(document, category_id: int | None) -> bool:
    if category_id is None:
        return bool(document.get("video_url")) and bool(get_source_category(document))

    if not document.get("video_url"):
        return False

    source_category = get_source_category(document)
    if not source_category:
        return False

    allowed_source_categories = LESSON_CATEGORY_SOURCE_MAP.get(category_id)
    if not allowed_source_categories:
        return False

    return source_category in allowed_source_categories


def get_lesson_query(category_id: int | None) -> dict:
    source_categories = sorted({
        source_category
        for category_sources in LESSON_CATEGORY_SOURCE_MAP.values()
        for source_category in category_sources
    })
    mongo_query = {
        "video_url": {"$exists": True, "$nin": [None, ""]},
        "category_name": {"$in": source_categories},
    }
    if category_id is not None:
        mongo_query["category_name"] = {"$in": LESSON_CATEGORY_SOURCE_MAP.get(category_id, [])}
    return mongo_query


def find_lesson_by_id(dictionary_collection, lesson_collection, lesson_id: int):
    lesson_id_as_text = str(lesson_id)
    return (
        dictionary_collection.find_one({"dictionary_id": lesson_id})
        or dictionary_collection.find_one({"dictionary_id": lesson_id_as_text})
        or dictionary_collection.find_one({"local_id": lesson_id})
        or dictionary_collection.find_one({"local_id": lesson_id_as_text})
        or dictionary_collection.find_one({"localId": lesson_id})
        or dictionary_collection.find_one({"localId": lesson_id_as_text})
        or lesson_collection.find_one({"lesson_id": lesson_id})
        or lesson_collection.find_one({"lesson_id": lesson_id_as_text})
    )


def get_lesson_progress_collection():
    return get_mongo_collection(LESSON_PROGRESS_COLLECTION)


def convert_lesson_progress_document(document) -> dict | None:
    if document is None:
        return None

    return {
        "user_id": to_int(document.get("user_id")),
        "category_id": to_int(document.get("category_id")),
        "lesson_id": to_int(document.get("lesson_id")),
        "lesson_index": to_int(document.get("lesson_index")),
        "word": document.get("word"),
        "category_name": document.get("category_name"),
        "updated_at": document.get("updated_at"),
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
    size: int = Query(default=20, ge=1, le=1000, description="Lessons per page."),
):
    try:
        category_collection, _ = ensure_default_lesson_data()
        dictionary_collection = get_dictionary_collection()
        category_documents = list(category_collection.find({}).sort("sort_order", ASCENDING))
        categories = [convert_category_document(category) for category in category_documents]

        if category_id is not None:
            category = category_collection.find_one({"category_id": category_id})
            if category is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Lesson category not found.",
                )

        mongo_query = get_lesson_query(category_id)
        all_lesson_documents = list(dictionary_collection.find(mongo_query).sort("word_name", ASCENDING))
        total = len(all_lesson_documents)
        start = (page - 1) * size
        lesson_documents = all_lesson_documents[start:start + size]
    except HTTPException:
        raise
    except PyMongoError as error:
        raise HTTPException(status_code=500, detail=f"Lesson MongoDB read failed: {error}")

    return LessonListResponseSchema(
        categories=categories,
        lessons=[
            LessonSummarySchema(**convert_lesson_summary_document(lesson, category_id))
            for lesson in lesson_documents
        ],
        selected_category_id=category_id,
        page=page,
        size=size,
        total=total,
    )


@router.get(
    "/progress",
    response_model=LessonProgressSchema | None,
    status_code=status.HTTP_200_OK,
)
async def read_lesson_progress(
    user_id: int = Query(..., description="Learning user id."),
    category_id: int | None = Query(default=None, description="Optional category id."),
):
    try:
        progress_collection = get_lesson_progress_collection()
        mongo_query = {"user_id": user_id}
        sort_order = [("updated_at", -1)]

        if category_id is not None:
            mongo_query["category_id"] = category_id

        progress = progress_collection.find_one(mongo_query, sort=sort_order)
    except PyMongoError as error:
        raise HTTPException(status_code=500, detail=f"Lesson progress MongoDB read failed: {error}")

    return convert_lesson_progress_document(progress)


@router.get(
    "/progress/latest",
    response_model=LessonProgressSchema | None,
    status_code=status.HTTP_200_OK,
)
async def read_latest_lesson_progress(
    user_id: int = Query(..., description="Learning user id."),
):
    try:
        progress = get_lesson_progress_collection().find_one(
            {"user_id": user_id},
            sort=[("updated_at", -1)],
        )
    except PyMongoError as error:
        raise HTTPException(status_code=500, detail=f"Lesson progress MongoDB read failed: {error}")

    return convert_lesson_progress_document(progress)


@router.post(
    "/progress",
    response_model=LessonProgressSchema,
    status_code=status.HTTP_200_OK,
)
async def save_lesson_progress(progress_create: LessonProgressSaveSchema):
    try:
        category_collection, lesson_collection = ensure_default_lesson_data()
        dictionary_collection = get_dictionary_collection()

        category = category_collection.find_one({"category_id": progress_create.category_id})
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson category not found.",
            )

        lesson = find_lesson_by_id(dictionary_collection, lesson_collection, progress_create.lesson_id)
        if lesson is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found.",
            )

        progress_document = {
            "user_id": progress_create.user_id,
            "category_id": progress_create.category_id,
            "category_name": category.get("name"),
            "lesson_id": progress_create.lesson_id,
            "lesson_index": progress_create.lesson_index,
            "word": progress_create.word or lesson.get("word") or lesson.get("word_name", ""),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        get_lesson_progress_collection().update_one(
            {
                "user_id": progress_create.user_id,
                "lesson_id": progress_create.lesson_id,
            },
            {"$set": progress_document},
            upsert=True,
        )
    except HTTPException:
        raise
    except PyMongoError as error:
        raise HTTPException(status_code=500, detail=f"Lesson progress MongoDB save failed: {error}")

    return LessonProgressSchema(**progress_document)


@router.get(
    "/{lesson_id}",
    response_model=LessonDetailSchema,
    status_code=status.HTTP_200_OK,
)
async def read_lesson_detail(lesson_id: int):
    try:
        category_collection, lesson_collection = ensure_default_lesson_data()
        dictionary_collection = get_dictionary_collection()
        lesson = find_lesson_by_id(dictionary_collection, lesson_collection, lesson_id)
        if lesson is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found.",
            )

        category_id = to_int(lesson.get("category_id"))
        if not category_id:
            for next_category in DEFAULT_LESSON_CATEGORIES:
                if is_valid_category_lesson(lesson, next_category["category_id"]):
                    category_id = next_category["category_id"]
                    break

        category = category_collection.find_one({"category_id": category_id})
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

@router.get("/progress/today-stats")
async def get_today_progress_stats(user_id: int = Query(...)):
    try:
        progress_collection = get_lesson_progress_collection()

        # 한국 시간 기준 오늘 날짜
        from datetime import timedelta
        korea_now = datetime.now(timezone.utc) + timedelta(hours=9)
        today = korea_now.strftime("%Y-%m-%d")

        all_progress = list(progress_collection.find({"user_id": user_id}))

        today_progress = [
            p for p in all_progress
            if p.get("updated_at", "")[:10] == today
        ]

        studied_count = len(today_progress)

        return {
            "studied_count": studied_count,
            "percent": min(round(studied_count / 50 * 100), 100)
        }
    except PyMongoError as error:
        raise HTTPException(status_code=500, detail=f"MongoDB read failed: {error}")

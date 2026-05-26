from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.lessons import (
    LessonCategorySchema,
    LessonDetailSchema,
    LessonListResponseSchema,
    LessonSummarySchema,
)

router = APIRouter()


LESSON_CATEGORIES = [
    {"category_id": 1, "name": "인사", "description": "인사 표현을 학습합니다.", "sort_order": 1},
    {"category_id": 2, "name": "일상생활", "description": "일상생활 표현을 학습합니다.", "sort_order": 2},
    {"category_id": 3, "name": "가족", "description": "가족 관련 표현을 학습합니다.", "sort_order": 3},
    {"category_id": 4, "name": "학교/직장", "description": "학교와 직장 표현을 학습합니다.", "sort_order": 4},
    {"category_id": 5, "name": "교통/장소", "description": "교통과 장소 표현을 학습합니다.", "sort_order": 5},
    {"category_id": 6, "name": "시간/날짜", "description": "시간과 날짜 표현을 학습합니다.", "sort_order": 6},
    {"category_id": 7, "name": "감정/상태", "description": "감정과 상태 표현을 학습합니다.", "sort_order": 7},
    {"category_id": 8, "name": "기타", "description": "기타 표현을 학습합니다.", "sort_order": 8},
]


LESSONS = [
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


def get_category(category_id: int) -> dict | None:
    return next(
        (category for category in LESSON_CATEGORIES if category["category_id"] == category_id),
        None,
    )


def get_lesson(lesson_id: int) -> dict | None:
    return next((lesson for lesson in LESSONS if lesson["lesson_id"] == lesson_id), None)


@router.get(
    "/categories",
    response_model=list[LessonCategorySchema],
    status_code=status.HTTP_200_OK,
)
async def read_lesson_categories():
    return sorted(LESSON_CATEGORIES, key=lambda category: category["sort_order"])


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
    filtered_lessons = LESSONS
    if category_id is not None:
        if not get_category(category_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson category not found.",
            )
        filtered_lessons = [
            lesson for lesson in LESSONS if lesson["category_id"] == category_id
        ]

    sorted_lessons = sorted(
        filtered_lessons,
        key=lambda lesson: (lesson["category_id"], lesson["sort_order"], lesson["lesson_id"]),
    )
    total = len(sorted_lessons)
    start = (page - 1) * size
    end = start + size

    return LessonListResponseSchema(
        categories=sorted(LESSON_CATEGORIES, key=lambda category: category["sort_order"]),
        lessons=[
            LessonSummarySchema(
                lesson_id=lesson["lesson_id"],
                category_id=lesson["category_id"],
                word=lesson["word"],
                sort_order=lesson["sort_order"],
            )
            for lesson in sorted_lessons[start:end]
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
    lesson = get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found.",
        )

    category = get_category(lesson["category_id"])
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson category not found.",
        )

    return LessonDetailSchema(
        lesson_id=lesson["lesson_id"],
        category_id=lesson["category_id"],
        category_name=category["name"],
        word=lesson["word"],
        video_url=lesson["video_url"],
        video_type=lesson["video_type"],
        description=lesson["description"],
        ai_model_key=lesson["ai_model_key"],
        sort_order=lesson["sort_order"],
    )

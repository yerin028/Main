from datetime import datetime, timezone
import random

from fastapi import APIRouter, HTTPException, Query, status

from app.core.mongo_database import get_mongo_collection
from app.models.quiz import QUIZ_COLLECTION, QUIZ_RESULT_COLLECTION
from app.schemas.quiz import (
    QuizCategorySchema,
    QuizResultCreateSchema,
    QuizResultSchema,
    QuizSchema,
)

router = APIRouter()

QUIZ_CATEGORIES = [
    {"category_id": 1, "name": "인사", "icon": "person", "description": "", "sort_order": 1},
    {"category_id": 2, "name": "일상생활", "icon": "hands", "description": "", "sort_order": 2},
    {"category_id": 3, "name": "가족", "icon": "family", "description": "", "sort_order": 3},
    {"category_id": 4, "name": "학교/직장", "icon": "school", "description": "", "sort_order": 4},
    {"category_id": 5, "name": "교통/장소", "icon": "bus", "description": "", "sort_order": 5},
    {"category_id": 6, "name": "시간/날짜", "icon": "clock", "description": "", "sort_order": 6},
    {"category_id": 7, "name": "감정/상태", "icon": "face", "description": "", "sort_order": 7},
    {"category_id": 8, "name": "기타", "icon": "pen", "description": "", "sort_order": 8},
]

DEFAULT_QUIZZES = [
    {
        "quiz_id": 101,
        "question": "다음 수어는 무슨 표현일까요?",
        "answer": "안녕하세요",
        "quiz_type": "인사",
        "lesson_id": 101,
        "lesson_id2": None,
        "video_url": None,
        "options": ["안녕하세요", "감사합니다", "미안합니다", "잘 지내세요"],
        "description": '"안녕하세요"가 정답입니다.',
        "sort_order": 1,
    },
    {
        "quiz_id": 102,
        "question": "다음 수어는 무슨 표현일까요?",
        "answer": "감사합니다",
        "quiz_type": "인사",
        "lesson_id": 102,
        "lesson_id2": None,
        "video_url": None,
        "options": ["안녕하세요", "감사합니다", "미안합니다", "잘 지내세요"],
        "description": '"감사합니다"가 정답입니다.',
        "sort_order": 2,
    },
]


def get_quiz_collection():
    return get_mongo_collection(QUIZ_COLLECTION)


def get_quiz_result_collection():
    return get_mongo_collection(QUIZ_RESULT_COLLECTION)


def get_category_by_id(category_id: int):
    return next(
        (category for category in QUIZ_CATEGORIES if category["category_id"] == category_id),
        None,
    )


def get_category_by_name(category_name: str | None):
    if not category_name:
        return None

    return next(
        (category for category in QUIZ_CATEGORIES if category["name"] == category_name),
        None,
    )


def next_sequence(collection, sequence_field: str):
    latest_document = collection.find_one(sort=[(sequence_field, -1)])
    if not latest_document:
        return 1

    return int(latest_document.get(sequence_field, 0)) + 1


def ensure_default_quizzes():
    collection = get_quiz_collection()
    if collection.count_documents({}) > 0:
        return

    collection.insert_many(DEFAULT_QUIZZES)


def serialize_quiz(document):
    category = get_category_by_name(document.get("quiz_type"))
    options = document.get("options") or []
    answer = document.get("answer")

    if answer and answer not in options:
        options = [answer, *options]

    return QuizSchema(
        quiz_id=document["quiz_id"],
        question=document["question"],
        answer=answer,
        quiz_type=document.get("quiz_type"),
        lesson_id=document.get("lesson_id"),
        lesson_id2=document.get("lesson_id2"),
        category_id=category["category_id"] if category else None,
        category_name=category["name"] if category else document.get("quiz_type"),
        video_url=document.get("video_url"),
        options=options,
        description=document.get("description"),
        sort_order=document.get("sort_order", 0),
    )


def serialize_quiz_result(document):
    return QuizResultSchema(
        result_id=document["result_id"],
        is_correct=document["is_correct"],
        answered_at=document["answered_at"],
        user_id=document.get("user_id"),
        quiz_id=document["quiz_id"],
        selected_option=document.get("selected_option"),
    )


@router.get(
    "/categories",
    response_model=list[QuizCategorySchema],
    status_code=status.HTTP_200_OK,
)
def read_quiz_categories():
    return sorted(QUIZ_CATEGORIES, key=lambda category: category["sort_order"])


@router.get(
    "",
    response_model=list[QuizSchema],
    status_code=status.HTTP_200_OK,
)
def read_quizzes(
    category_id: int | None = Query(default=None, description="Frontend category id."),
    quiz_type: str | None = Query(default=None, description="Quiz type/category name."),
):
    ensure_default_quizzes()
    query = {}

    if category_id is not None:
        category = get_category_by_id(category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz category not found.",
            )
        query["quiz_type"] = category["name"]
    elif quiz_type:
        query["quiz_type"] = quiz_type

    documents = list(get_quiz_collection().find(query))
    random.shuffle(documents)
    return [serialize_quiz(document) for document in documents]


@router.post(
    "/results",
    response_model=QuizResultSchema,
    status_code=status.HTTP_201_CREATED,
)
def create_quiz_result(result_create: QuizResultCreateSchema):
    ensure_default_quizzes()

    if not get_quiz_collection().find_one({"quiz_id": result_create.quiz_id}):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found.",
        )

    collection = get_quiz_result_collection()
    document = {
        "result_id": next_sequence(collection, "result_id"),
        "is_correct": result_create.is_correct,
        "answered_at": datetime.now(timezone.utc),
        "user_id": result_create.user_id,
        "quiz_id": result_create.quiz_id,
        "selected_option": result_create.selected_option,
    }
    collection.insert_one(document)

    return serialize_quiz_result(document)

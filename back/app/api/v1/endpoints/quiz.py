import random
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from pymongo.errors import PyMongoError

from app.core.mongo_database import get_dictionary_collection, get_mongo_collection
from app.core.lesson_categories import DEFAULT_LESSON_CATEGORIES, get_lesson_query
from app.schemas.quiz import (
    QuizCategorySchema,
    QuizResultCreateSchema,
    QuizResultSchema,
    QuizSchema,
)

router = APIRouter()

QUIZ_RESULT_COLLECTION = "quiz_results"
OPTION_COUNT = 4


def get_quiz_result_collection():
    return get_mongo_collection(QUIZ_RESULT_COLLECTION)


def next_sequence(collection, sequence_field: str):
    latest_document = collection.find_one(sort=[(sequence_field, -1)])
    if not latest_document:
        return 1
    return int(latest_document.get(sequence_field, 0)) + 1


def get_category_by_id(category_id: int):
    return next(
        (category for category in DEFAULT_LESSON_CATEGORIES if category["category_id"] == category_id),
        None,
    )


def normalize_video_url(video_url: str | None) -> str | None:
    if not video_url:
        return None
    return video_url.replace("http://sldict.korean.go.kr", "https://sldict.korean.go.kr")


def build_quiz_from_words(words: list[dict], category: dict, quiz_id_start: int) -> list[dict]:
    quizzes = []
    word_pool = [w for w in words if w.get("word") or w.get("word_name")]

    if len(word_pool) < OPTION_COUNT:
        return quizzes

    shuffled_words = word_pool.copy()
    random.shuffle(shuffled_words)

    for index, answer_word in enumerate(shuffled_words):
        answer_text = answer_word.get("word") or answer_word.get("word_name")
        other_words = [
            w for w in word_pool
            if (w.get("word") or w.get("word_name")) != answer_text
        ]
        if len(other_words) < OPTION_COUNT - 1:
            continue

        wrong_options = random.sample(other_words, OPTION_COUNT - 1)
        options = [answer_text] + [w.get("word") or w.get("word_name") for w in wrong_options]
        random.shuffle(options)

        quizzes.append({
            "quiz_id": quiz_id_start + index,
            "question": "다음 수어가 의미하는 것은?",
            "answer": answer_text,
            "quiz_type": category["name"],
            "category_id": category["category_id"],
            "category_name": category["name"],
            "video_url": normalize_video_url(answer_word.get("video_url")),
            "options": options,
            "description": answer_word.get("description") or answer_word.get("definition") or f'"{answer_text}"가 정답입니다.',
            "sort_order": index + 1,
        })

    return quizzes


@router.get(
    "/categories",
    response_model=list[QuizCategorySchema],
    status_code=status.HTTP_200_OK,
)
def read_quiz_categories():
    return sorted(DEFAULT_LESSON_CATEGORIES, key=lambda category: category["sort_order"])


@router.get(
    "",
    response_model=list[QuizSchema],
    status_code=status.HTTP_200_OK,
)
def read_quizzes(
    category_id: int | None = Query(default=None, description="Frontend category id."),
):
    if category_id is None:
        raise HTTPException(status_code=400, detail="category_id is required.")

    category = get_category_by_id(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Quiz category not found.")

    try:
        dictionary_collection = get_dictionary_collection()
        mongo_query = get_lesson_query(category_id)
        words = list(dictionary_collection.find(mongo_query))
    except PyMongoError as error:
        raise HTTPException(status_code=500, detail=f"Dictionary MongoDB read failed: {error}")

    quizzes = build_quiz_from_words(words, category, quiz_id_start=category_id * 1000)

    if not quizzes:
        raise HTTPException(
            status_code=404,
            detail="이 카테고리는 학습 단어가 부족하여 퀴즈를 생성할 수 없습니다.",
        )

    random.shuffle(quizzes)
    return [QuizSchema(**quiz) for quiz in quizzes[:10]]


@router.post(
    "/results",
    response_model=QuizResultSchema,
    status_code=status.HTTP_201_CREATED,
)
def create_quiz_result(result_create: QuizResultCreateSchema):
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

    return QuizResultSchema(**document)
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import PyMongoError
from sqlalchemy.orm import Session

from app.core.mongo_database import get_mongo_collection
from app.core.mysql_database import get_db
from app.models.cs import CS_ANSWER_COLLECTION, CS_QUESTION_COLLECTION
from app.models.users import User
from app.models.withdrawal import UserWithdrawal
from app.schemas.cs import (
    CSAnswerCreate,
    CSAnswerSchema,
    CSQuestionCreate,
    CSQuestionSchema,
)

router = APIRouter()


def get_question_collection():
    return get_mongo_collection(CS_QUESTION_COLLECTION)


def get_answer_collection():
    return get_mongo_collection(CS_ANSWER_COLLECTION)


def next_sequence(collection, sequence_field: str):
    latest_document = collection.find_one(sort=[(sequence_field, -1)])
    if not latest_document:
        return 1

    return int(latest_document.get(sequence_field, 0)) + 1


def get_user_snapshot(db: Session, user_id: int | None):
    if user_id is None:
        return {}

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return {
        "user_id": user.user_id,
        "user_name": user.name,
        "user_email": user.email,
    }


def serialize_answer(document):
    return CSAnswerSchema(
        answer_id=int(document.get("answer_id", 0)),
        content=document.get("content") or "",
        created_at=document.get("created_at"),
        user_id=document.get("user_id"),
        user_name=document.get("user_name"),
        user_email=document.get("user_email"),
        question_id=document.get("question_id"),
    )


def get_answers(question_id: int):
    documents = get_answer_collection().find({"question_id": question_id}).sort("answer_id", 1)
    return [serialize_answer(document) for document in documents]


def serialize_question(document):
    question_id = int(document.get("question_id", 0))
    answers = get_answers(question_id)

    return CSQuestionSchema(
        question_id=question_id,
        content=document.get("content") or document.get("title") or "",
        created_at=document.get("created_at"),
        user_id=document.get("user_id"),
        user_name=document.get("user_name"),
        user_email=document.get("user_email"),
        answer_status="답변 완료" if answers else "답변 대기",
        answers=answers,
    )


@router.post(
    "/questions",
    response_model=CSQuestionSchema,
    status_code=status.HTTP_201_CREATED,
)
def create_question(
    question_create: CSQuestionCreate,
    db: Session = Depends(get_db),
):
    collection = get_question_collection()
    user_snapshot = get_user_snapshot(db, question_create.user_id)

    try:
        document = {
            "question_id": next_sequence(collection, "question_id"),
            "title": question_create.content,
            "content": question_create.content,
            "created_at": datetime.now(timezone.utc),
            **user_snapshot,
        }
        collection.insert_one(document)
    except PyMongoError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create question: {error}",
        ) from error

    return CSQuestionSchema(
        question_id=document["question_id"],
        content=document.get("content") or document.get("title") or "",
        created_at=document.get("created_at"),
        user_id=document.get("user_id"),
        user_name=document.get("user_name"),
        user_email=document.get("user_email"),
        answer_status="답변 대기",
        answers=[],
    )


@router.get(
    "/questions",
    response_model=list[CSQuestionSchema],
    status_code=status.HTTP_200_OK,
)
def read_questions(user_id: int | None = None):
    try:
        query = {}
        if user_id is not None:
            query["user_id"] = user_id
        documents = get_question_collection().find(query).sort("question_id", -1)
        return [serialize_question(document) for document in documents]
    except PyMongoError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read questions: {error}",
        ) from error


@router.post(
    "/answers",
    response_model=CSAnswerSchema,
    status_code=status.HTTP_201_CREATED,
)
def create_answer(
    answer_create: CSAnswerCreate,
    db: Session = Depends(get_db),
):
    user_snapshot = get_user_snapshot(db, answer_create.user_id)

    try:
        question = get_question_collection().find_one({"question_id": answer_create.question_id})
    except PyMongoError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read question: {error}",
        ) from error

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found.",
        )

    collection = get_answer_collection()

    try:
        document = {
            "answer_id": next_sequence(collection, "answer_id"),
            "content": answer_create.content,
            "created_at": datetime.now(timezone.utc),
            **user_snapshot,
            "question_id": answer_create.question_id,
        }
        collection.insert_one(document)
    except PyMongoError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create answer: {error}",
        ) from error

    return serialize_answer(document)


# 탈퇴
@router.post("/withdraw", status_code=status.HTTP_200_OK)
def withdraw_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    existing = db.query(UserWithdrawal).filter(UserWithdrawal.user_id == user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 탈퇴한 사용자입니다.")

    # 유저 정보 통째로 복사
    withdrawal = UserWithdrawal(
        user_id               = user.user_id,
        email                 = user.email,
        password              = user.password,
        social_provider       = user.social_provider,
        social_id             = user.social_id,
        name                  = user.name,
        role                  = user.role,
        customer_key          = user.customer_key,
        billing_key           = user.billing_key,
        subscription_end_date = user.subscription_end_date,
        created_at            = user.created_at,
    )
    db.add(withdrawal)
    db.commit()
    return {"message": "탈퇴가 완료되었습니다."}
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.mysql_database import engine, get_db
from app.models.cs import CSAnswer, CSQuestion
from app.schemas.cs import (
    CSAnswerCreate,
    CSAnswerSchema,
    CSQuestionCreate,
    CSQuestionSchema,
)

router = APIRouter()


def ensure_cs_tables():
    CSQuestion.__table__.create(bind=engine, checkfirst=True)
    CSAnswer.__table__.create(bind=engine, checkfirst=True)


def to_question_schema(question: CSQuestion):
    return CSQuestionSchema(
        question_id=question.question_id,
        content=question.content,
        created_at=question.created_at,
        user_id=question.user_id,
        answer_status="답변 완료" if question.answers else "답변 대기",
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
    ensure_cs_tables()

    question = CSQuestion(
        content=question_create.content,
        user_id=question_create.user_id,
    )

    try:
        db.add(question)
        db.commit()
        db.refresh(question)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create question.",
        ) from error

    return to_question_schema(question)


@router.get(
    "/questions",
    response_model=list[CSQuestionSchema],
    status_code=status.HTTP_200_OK,
)
def read_questions(db: Session = Depends(get_db)):
    ensure_cs_tables()

    questions = (
        db.query(CSQuestion)
        .order_by(CSQuestion.question_id.desc())
        .all()
    )
    return [to_question_schema(question) for question in questions]


@router.post(
    "/answers",
    response_model=CSAnswerSchema,
    status_code=status.HTTP_201_CREATED,
)
def create_answer(
    answer_create: CSAnswerCreate,
    db: Session = Depends(get_db),
):
    ensure_cs_tables()

    question = (
        db.query(CSQuestion)
        .filter(CSQuestion.question_id == answer_create.question_id)
        .first()
    )

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found.",
        )

    answer = CSAnswer(
        content=answer_create.content,
        user_id=answer_create.user_id,
        question_id=answer_create.question_id,
    )

    try:
        db.add(answer)
        db.commit()
        db.refresh(answer)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create answer.",
        ) from error

    return answer


from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from database import (
    sessions_collection,
    questions_collection,
    attempts_collection,
    knowledge_collection
)
from dependencies import get_current_user
from schemas import QuestionCreate, AnswerSubmit


router = APIRouter(prefix="/api/learning", tags=["Learning"])


def valid_id(value: str) -> bool:
    return ObjectId.is_valid(value)


@router.post("/{session_id}/questions")
async def add_question(
    session_id: str,
    data: QuestionCreate,
    user=Depends(get_current_user)
):
    if not valid_id(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")

    session = await sessions_collection.find_one({
        "_id": ObjectId(session_id),
        "user_id": user["_id"]
    })

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if data.correct_option >= len(data.options):
        raise HTTPException(
            status_code=400,
            detail="Correct option is outside the options list"
        )

    question = {
        "session_id": ObjectId(session_id),
        "user_id": user["_id"],
        "concept": data.concept,
        "prompt": data.prompt,
        "options": data.options,
        "correct_option": data.correct_option,
        "explanation": data.explanation,
        "difficulty": data.difficulty,
        "created_at": datetime.now(timezone.utc)
    }

    result = await questions_collection.insert_one(question)

    return {"id": str(result.inserted_id), "message": "Question created"}


@router.get("/{session_id}/questions")
async def list_questions(
    session_id: str,
    user=Depends(get_current_user)
):
    if not valid_id(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")

    session = await sessions_collection.find_one({
        "_id": ObjectId(session_id),
        "user_id": user["_id"]
    })

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    cursor = questions_collection.find({
        "session_id": ObjectId(session_id),
        "user_id": user["_id"]
    })

    result = []

    async for q in cursor:
        # Never send the answer key to the frontend before submission.
        result.append({
            "id": str(q["_id"]),
            "concept": q["concept"],
            "prompt": q["prompt"],
            "options": q["options"],
            "difficulty": q["difficulty"]
        })

    return result


@router.post("/{session_id}/answer")
async def submit_answer(
    session_id: str,
    data: AnswerSubmit,
    user=Depends(get_current_user)
):
    if not valid_id(session_id) or not valid_id(data.question_id):
        raise HTTPException(status_code=400, detail="Invalid ID")

    session = await sessions_collection.find_one({
        "_id": ObjectId(session_id),
        "user_id": user["_id"]
    })

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    question = await questions_collection.find_one({
        "_id": ObjectId(data.question_id),
        "session_id": ObjectId(session_id),
        "user_id": user["_id"]
    })

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if data.selected_option >= len(question["options"]):
        raise HTTPException(status_code=400, detail="Invalid option")

    correct = data.selected_option == question["correct_option"]

    attempt = {
        "user_id": user["_id"],
        "session_id": ObjectId(session_id),
        "question_id": question["_id"],
        "concept": question["concept"],
        "selected_option": data.selected_option,
        "is_correct": correct,
        "created_at": datetime.now(timezone.utc)
    }

    await attempts_collection.insert_one(attempt)

    # Basic evidence counter for the initial learner profile.
    # This is NOT yet a trained knowledge-tracing model.
    await knowledge_collection.update_one(
        {
            "user_id": user["_id"],
            "concept": question["concept"]
        },
        {
            "$inc": {
                "attempts": 1,
                "correct_attempts": int(correct)
            },
            "$set": {
                "updated_at": datetime.now(timezone.utc)
            },
            "$setOnInsert": {
                "user_id": user["_id"],
                "concept": question["concept"]
            }
        },
        upsert=True
    )

    return {
        "correct": correct,
        "correct_option": question["correct_option"],
        "explanation": question["explanation"]
    }


@router.get("/profile")
async def get_learner_profile(user=Depends(get_current_user)):
    cursor = knowledge_collection.find({"user_id": user["_id"]})

    profile = []

    async for item in cursor:
        attempts = item.get("attempts", 0)
        correct = item.get("correct_attempts", 0)

        profile.append({
            "concept": item["concept"],
            "attempts": attempts,
            "correct_attempts": correct,
            "accuracy": round(correct / attempts, 3) if attempts else 0
        })

    return profile
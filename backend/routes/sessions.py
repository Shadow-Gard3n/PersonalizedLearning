
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from database import sessions_collection, attempts_collection
from dependencies import get_current_user
from schemas import SessionCreate


router = APIRouter(prefix="/api/sessions", tags=["Learning Sessions"])


@router.post("/")
async def create_session(
    data: SessionCreate,
    user=Depends(get_current_user)
):
    session = {
        "user_id": user["_id"],
        "topic": data.topic.strip(),
        "learning_goal": data.learning_goal.strip(),
        "status": "active",
        "created_at": datetime.now(timezone.utc),
    }

    result = await sessions_collection.insert_one(session)

    return {
        "id": str(result.inserted_id),
        "topic": session["topic"],
        "learning_goal": session["learning_goal"],
        "status": session["status"]
    }


@router.get("/")
async def list_sessions(user=Depends(get_current_user)):
    cursor = sessions_collection.find(
        {"user_id": user["_id"]}
    ).sort("created_at", -1)

    sessions = []

    async for session in cursor:
        sessions.append({
            "id": str(session["_id"]),
            "topic": session["topic"],
            "learning_goal": session["learning_goal"],
            "status": session["status"],
            "created_at": session["created_at"].isoformat()
        })

    return sessions


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    user=Depends(get_current_user)
):
    if not ObjectId.is_valid(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")

    session = await sessions_collection.find_one({
        "_id": ObjectId(session_id),
        "user_id": user["_id"]
    })

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "id": str(session["_id"]),
        "topic": session["topic"],
        "learning_goal": session["learning_goal"],
        "status": session["status"],
        "created_at": session["created_at"].isoformat()
    }


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user=Depends(get_current_user)
):
    if not ObjectId.is_valid(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")

    session_filter = {
        "_id": ObjectId(session_id),
        "user_id": user["_id"]
    }

    result = await sessions_collection.delete_one(session_filter)

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")

    await attempts_collection.delete_many({
        "session_id": ObjectId(session_id),
        "user_id": user["_id"]
    })

    return {"message": "Session and its attempts deleted"}
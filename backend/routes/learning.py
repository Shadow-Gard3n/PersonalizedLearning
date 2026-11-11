from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from database import (
    sessions_collection,
    questions_collection,
    attempts_collection,
    knowledge_collection
)
from dependencies import get_current_user
from schemas import DoubtRequest
from services.agents import (
    planner_agent, 
    content_creator_agent,
    interactive_tutor_agent,
    assessment_generator_agent, 
    vision_evaluator_agent
)

router = APIRouter(prefix="/api/learning", tags=["Learning"])

def valid_id(value: str) -> bool:
    return ObjectId.is_valid(value)


@router.post("/{session_id}/plan")
async def generate_syllabus(session_id: str, user=Depends(get_current_user)):
    """Step 1: Planner Agent creates the roadmap based on user's weak topics."""
    if not valid_id(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")

    session = await sessions_collection.find_one({"_id": ObjectId(session_id), "user_id": user["_id"]})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Fetch user profile for personalization
    cursor = knowledge_collection.find({"user_id": user["_id"]})
    user_profile = [item async for item in cursor]

    # Agent generates the syllabus
    plan = await planner_agent(session["topic"], user_profile)
    
    # Save plan to database session
    await sessions_collection.update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {
            "overview": plan["overview"],
            "subtopics": plan["subtopics"],
            "current_index": 0
        }}
    )
    return plan


@router.post("/{session_id}/content")
async def generate_current_content(session_id: str, user=Depends(get_current_user)):
    """Step 2: Content Agent generates material for the active subtopic only."""
    if not valid_id(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")

    session = await sessions_collection.find_one({"_id": ObjectId(session_id), "user_id": user["_id"]})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    idx = session.get("current_index", 0)
    subtopics = session.get("subtopics", [])
    
    if idx >= len(subtopics):
        return {"message": "All subtopics completed for this session.", "completed": True}
        
    current_subtopic = subtopics[idx]
    
    # If material already exists, return it, otherwise generate it
    if not current_subtopic.get("material"):
        material = await content_creator_agent(
            current_subtopic["title"], 
            current_subtopic["description"], 
            session["overview"]
        )
        subtopics[idx]["material"] = material
        subtopics[idx]["status"] = "active"
        
        await sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"subtopics": subtopics}}
        )
    else:
        material = current_subtopic["material"]

    return {
        "subtopic_title": current_subtopic["title"],
        "material": material,
        "completed": False
    }


@router.post("/{session_id}/doubt")
async def ask_doubt(session_id: str, data: DoubtRequest, user=Depends(get_current_user)):
    """Step 3: Interactive Tutor Agent answers questions strictly based on current material."""
    if not valid_id(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")

    answer = await interactive_tutor_agent(data.question, data.current_material, data.chat_history)
    return {"answer": answer}


@router.post("/{session_id}/generate-questions")
async def generate_subtopic_questions(session_id: str, user=Depends(get_current_user)):
    """Step 4: Assessment Agent creates questions for the current subtopic."""
    if not valid_id(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")

    session = await sessions_collection.find_one({"_id": ObjectId(session_id), "user_id": user["_id"]})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    idx = session.get("current_index", 0)
    subtopics = session.get("subtopics", [])
    
    if idx >= len(subtopics):
        raise HTTPException(status_code=400, detail="No active subtopic to generate questions for.")
        
    current_subtopic = subtopics[idx]
    
    if not current_subtopic.get("material"):
        raise HTTPException(status_code=400, detail="Must generate content before questions.")

    generated_questions = await assessment_generator_agent(
        current_subtopic["material"], 
        current_subtopic["title"]
    )

    question_ids = []
    for q_data in generated_questions:
        q_data.update({
            "session_id": ObjectId(session_id),
            "user_id": user["_id"],
            "subtopic_title": current_subtopic["title"],
            "created_at": datetime.now(timezone.utc)
        })
        result = await questions_collection.insert_one(q_data)
        question_ids.append(str(result.inserted_id))

    return {"message": "Questions generated successfully", "question_ids": question_ids}


@router.post("/{session_id}/evaluate-upload")
async def evaluate_uploaded_notebook(
    session_id: str, 
    file: UploadFile = File(...), 
    user=Depends(get_current_user)
):
    """Step 5: Vision Agent evaluates handwritten answers and updates the knowledge graph."""
    if not valid_id(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")

    session = await sessions_collection.find_one({"_id": ObjectId(session_id), "user_id": user["_id"]})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get the current subtopic to fetch relevant questions
    idx = session.get("current_index", 0)
    subtopics = session.get("subtopics", [])
    current_subtopic_title = subtopics[idx]["title"] if idx < len(subtopics) else ""

    # Gather context (the questions the user was supposed to answer for this subtopic)
    cursor = questions_collection.find({
        "session_id": ObjectId(session_id), 
        "user_id": user["_id"],
        "subtopic_title": current_subtopic_title
    })
    session_questions = [q async for q in cursor]
    
    if not session_questions:
        raise HTTPException(status_code=400, detail="No questions found for the current subtopic to evaluate.")

    # Read image
    image_bytes = await file.read()

    # Vision Agent evaluates the handwritten answers
    # Exclude MongoDB ObjectIds before passing to JSON serializer
    safe_questions = [{k: v for k, v in q.items() if k != "_id"} for q in session_questions]
    evaluation = await vision_evaluator_agent(image_bytes, safe_questions)

    # Update Learner Profile Knowledge Graph based on Agent's finding of weak topics
    for topic in evaluation["weak_topics"]:
        await knowledge_collection.update_one(
            {
                "user_id": user["_id"],
                "concept": topic
            },
            {
                "$inc": {"attempts": 1, "correct_attempts": 0}, 
                "$set": {"updated_at": datetime.now(timezone.utc), "status": "weak"},
                "$setOnInsert": {"user_id": user["_id"], "concept": topic}
            },
            upsert=True
        )

    # Log the attempt
    await attempts_collection.insert_one({
        "user_id": user["_id"],
        "session_id": ObjectId(session_id),
        "subtopic_title": current_subtopic_title,
        "score": evaluation["score"],
        "feedback": evaluation["feedback"],
        "weak_topics_identified": evaluation["weak_topics"],
        "created_at": datetime.now(timezone.utc)
    })

    return evaluation


@router.post("/{session_id}/next")
async def advance_to_next_subtopic(session_id: str, user=Depends(get_current_user)):
    """Step 6: Marks current subtopic complete and moves pointer to the next one."""
    if not valid_id(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")

    session = await sessions_collection.find_one({"_id": ObjectId(session_id), "user_id": user["_id"]})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    idx = session.get("current_index", 0)
    subtopics = session.get("subtopics", [])
    
    if idx < len(subtopics):
        subtopics[idx]["status"] = "completed"
        
    new_index = idx + 1
    await sessions_collection.update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {
            "subtopics": subtopics,
            "current_index": new_index
        }}
    )
    
    is_finished = new_index >= len(subtopics)
    return {
        "message": "Advanced to next subtopic" if not is_finished else "Session fully completed", 
        "new_index": new_index,
        "session_finished": is_finished
    }


@router.get("/profile")
async def get_learner_profile(user=Depends(get_current_user)):
    """Fetches the user's complete knowledge mastery graph."""
    cursor = knowledge_collection.find({"user_id": user["_id"]})

    profile = []
    async for item in cursor:
        attempts = item.get("attempts", 0)
        correct = item.get("correct_attempts", 0)

        profile.append({
            "concept": item["concept"],
            "attempts": attempts,
            "correct_attempts": correct,
            "accuracy": round(correct / attempts, 3) if attempts else 0,
            "status": item.get("status", "developing")
        })

    return profile


@router.get("/{session_id}/questions")
async def list_questions(session_id: str, user=Depends(get_current_user)):
    """Lists questions for the current session (frontend read-only)."""
    if not valid_id(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")

    session = await sessions_collection.find_one({"_id": ObjectId(session_id), "user_id": user["_id"]})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    cursor = questions_collection.find({
        "session_id": ObjectId(session_id),
        "user_id": user["_id"]
    })

    result = []
    async for q in cursor:
        result.append({
            "id": str(q["_id"]),
            "subtopic_title": q.get("subtopic_title", ""),
            "concept": q["concept"],
            "prompt": q["prompt"],
            "options": q["options"],
            "difficulty": q["difficulty"]
        })

    return result
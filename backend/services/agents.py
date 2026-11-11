import os
import json
import io
import base64
import httpx
from google import genai
from google.genai import types
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

# --- Configurations ---

# Gemini requires v1beta for JSON schema generation
gemini_client = genai.Client(http_options={'api_version': 'v1beta'})
GEMINI_MODEL = 'gemini-2.5-flash'

# Local Model Setup (Ollama default port)
USE_LOCAL_MODEL = os.getenv("USE_LOCAL_MODEL", "false").lower() == "true"
LOCAL_TEXT_MODEL = os.getenv("LOCAL_TEXT_MODEL", "llama3")
LOCAL_VISION_MODEL = os.getenv("LOCAL_VISION_MODEL", "llava")
OLLAMA_URL = "http://localhost:11434/api/generate"


async def _call_local_model(prompt: str, model: str, format_json: bool = False, image_bytes: bytes = None) -> str:
    """Helper to route requests to a local Ollama instance."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    if format_json:
        payload["format"] = "json"
        
    if image_bytes:
        payload["images"] = [base64.b64encode(image_bytes).decode('utf-8')]

    async with httpx.AsyncClient() as client:
        response = await client.post(OLLAMA_URL, json=payload, timeout=120.0)
        response.raise_for_status()
        return response.json()["response"]


# --- Agents ---

async def planner_agent(topic: str, user_profile: list) -> dict:
    """Agent 1: Generates the overview and breaks the topic into sequential sub-topics."""
    prompt = f"""
    You are an expert curriculum planner. 
    Topic: {topic}
    Student's historical performance: {user_profile}
    
    Create a study plan. Break the topic into 3 to 5 logical sub-topics.
    Return ONLY a JSON object with this exact structure:
    {{
        "overview": "A brief summary of the whole session",
        "subtopics": [
            {{"title": "Subtopic 1", "description": "What this covers", "status": "pending"}},
            {{"title": "Subtopic 2", "description": "What this covers", "status": "pending"}}
        ]
    }}
    """
    
    if USE_LOCAL_MODEL:
        response_text = await _call_local_model(prompt, LOCAL_TEXT_MODEL, format_json=True)
        return json.loads(response_text)

    response = await gemini_client.aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(response.text)


async def content_creator_agent(subtopic_title: str, subtopic_desc: str, overview: str) -> str:
    """Agent 2: Generates material for ONE specific subtopic."""
    prompt = f"""
    You are an expert educator. We are currently studying: {overview}
    Generate detailed, engaging study material ONLY for this specific subtopic:
    Title: {subtopic_title}
    Description: {subtopic_desc}
    
    Format using markdown. Do not cover future subtopics.
    """
    
    if USE_LOCAL_MODEL:
        return await _call_local_model(prompt, LOCAL_TEXT_MODEL)

    response = await gemini_client.aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )
    return response.text


async def interactive_tutor_agent(doubt: str, material: str, history: list) -> str:
    """Agent 3: Answers user doubts strictly based on the current material."""
    system_instruction = f"You are a helpful tutor. The student is reading this material: {material}. Answer their doubts clearly and concisely. If they ask about something completely off-topic, gently guide them back."
    
    if USE_LOCAL_MODEL:
        # Construct a raw text prompt with chat history for the local model
        history_text = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])
        prompt = f"{system_instruction}\n\nChat History:\n{history_text}\n\nStudent Doubt: {doubt}\n\nTutor:"
        return await _call_local_model(prompt, LOCAL_TEXT_MODEL)

    # Convert history for Gemini
    formatted_history = [{"role": msg["role"], "parts": [{"text": msg["content"]}]} for msg in history]
    
    chat = gemini_client.aio.chats.create(
        model=GEMINI_MODEL,
        config=types.GenerateContentConfig(system_instruction=system_instruction),
        history=formatted_history
    )
    
    response = await chat.send_message(doubt)
    return response.text


async def assessment_generator_agent(material: str, concept: str) -> list:
    """Agent 4: Creates questions based on the generated subtopic material."""
    prompt = f"""
    Based on the following learning material, generate 3 multiple-choice questions to test comprehension.
    Main concept: {concept}
    
    Material:
    {material}
    
    You MUST output strictly in JSON format. The JSON must be an array of objects. 
    Each object must have these keys: "concept" (string), "prompt" (string), "options" (array of 4 strings), "correct_option" (integer 0-3), "explanation" (string), "difficulty" (string: easy, medium, or hard).
    """
    
    if USE_LOCAL_MODEL:
        response_text = await _call_local_model(prompt, LOCAL_TEXT_MODEL, format_json=True)
        return json.loads(response_text)

    response = await gemini_client.aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "concept": {"type": "STRING"},
                        "prompt": {"type": "STRING"},
                        "options": {"type": "ARRAY", "items": {"type": "STRING"}},
                        "correct_option": {"type": "INTEGER", "description": "Index of the correct option (0-3)"},
                        "explanation": {"type": "STRING"},
                        "difficulty": {"type": "STRING", "enum": ["easy", "medium", "hard"]}
                    },
                    "required": ["concept", "prompt", "options", "correct_option", "explanation", "difficulty"]
                }
            }
        )
    )
    return json.loads(response.text)


async def vision_evaluator_agent(image_bytes: bytes, session_questions: list) -> dict:
    """Agent 5: Uses a Vision model to read handwritten notes, compare them to questions, and evaluate."""
    prompt = f"""
    You are an AI grader. The user has uploaded an image of their handwritten answers to a quiz.
    Here are the original questions and correct answers for context:
    {json.dumps(session_questions, indent=2)}
    
    Read the handwritten text in the image. Evaluate if their answers are correct.
    Return your evaluation strictly in the following JSON format. Identify any specific sub-concepts they struggled with.
    Required keys: "score" (number), "feedback" (string), "weak_topics" (array of strings), "is_correct" (boolean).
    """

    if USE_LOCAL_MODEL:
        response_text = await _call_local_model(prompt, LOCAL_VISION_MODEL, format_json=True, image_bytes=image_bytes)
        return json.loads(response_text)

    img = Image.open(io.BytesIO(image_bytes))
    response = await gemini_client.aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=[prompt, img],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "score": {"type": "NUMBER"},
                    "feedback": {"type": "STRING"},
                    "weak_topics": {
                        "type": "ARRAY", 
                        "items": {"type": "STRING"},
                        "description": "Specific concepts the student got wrong and needs to review."
                    },
                    "is_correct": {"type": "BOOLEAN"}
                },
                "required": ["score", "feedback", "weak_topics", "is_correct"]
            }
        )
    )
    return json.loads(response.text)
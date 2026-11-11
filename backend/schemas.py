from pydantic import BaseModel, EmailStr, Field
from typing import Literal, List, Optional


class UserRegister(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class SessionCreate(BaseModel):
    topic: str = Field(min_length=2, max_length=150)
    learning_goal: str = Field(default="", max_length=500)


class QuestionCreate(BaseModel):
    concept: str = Field(min_length=1, max_length=150)
    prompt: str = Field(min_length=1, max_length=3000)
    options: List[str] = Field(min_length=2, max_length=6)
    correct_option: int = Field(ge=0)
    explanation: str = Field(default="", max_length=3000)
    difficulty: Literal["easy", "medium", "hard"] = "easy"


class AnswerSubmit(BaseModel):
    question_id: str
    selected_option: int = Field(ge=0)


# --- Knowledge Tracking ---

class TopicMastery(BaseModel):
    concept: str
    attempts: int = 0
    correct_attempts: int = 0
    status: Literal["weak", "developing", "strong"] = "developing"


# --- Session Management (Step-by-Step Agent Flow) ---

class SubTopic(BaseModel):
    title: str
    description: str
    status: Literal["pending", "active", "completed"] = "pending"
    material: Optional[str] = None


class GenerateSyllabusResponse(BaseModel):
    overview: str
    subtopics: List[SubTopic]


class GenerateContentResponse(BaseModel):
    subtopic_title: str
    material: str


# --- Interactive Tutor ---

class ChatMessage(BaseModel):
    role: Literal["user", "model"]
    content: str


class DoubtRequest(BaseModel):
    question: str
    subtopic_title: str
    current_material: str
    chat_history: List[ChatMessage] = []


# --- Vision Evaluation ---

class EvaluationResponse(BaseModel):
    score: float = Field(ge=0.0, le=100.0)
    feedback: str
    weak_topics: List[str]
    is_correct: bool
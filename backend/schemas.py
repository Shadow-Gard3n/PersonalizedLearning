
from pydantic import BaseModel, EmailStr, Field
from typing import Literal


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
    options: list[str] = Field(min_length=2, max_length=6)
    correct_option: int = Field(ge=0)
    explanation: str = Field(default="", max_length=3000)
    difficulty: Literal["easy", "medium", "hard"] = "easy"


class AnswerSubmit(BaseModel):
    question_id: str
    selected_option: int = Field(ge=0)
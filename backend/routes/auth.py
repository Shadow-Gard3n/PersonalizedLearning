
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends
from dependencies import get_current_user

from database import users_collection
from schemas import UserRegister, UserLogin
from security import (
    hash_password,
    verify_password,
    create_access_token
)


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister):
    email = data.email.lower()

    existing = await users_collection.find_one({"email": email})

    if existing:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists"
        )

    user = {
        "name": data.name,
        "email": email,
        "password_hash": hash_password(data.password),
        "created_at": datetime.now(timezone.utc),
    }

    result = await users_collection.insert_one(user)

    return {
        "message": "Registration successful",
        "user_id": str(result.inserted_id)
    }


@router.post("/login")
async def login(data: UserLogin):
    email = data.email.lower()

    user = await users_collection.find_one({"email": email})

    if not user or not verify_password(
        data.password,
        user["password_hash"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )

    token = create_access_token(str(user["_id"]))

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"]
        }
    }


@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"]
    }
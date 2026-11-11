from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from config import settings
from database import users_collection
from security import ALGORITHM


security_scheme = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)):
    token = credentials.credentials
    
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGORITHM]
        )
        user_id = payload.get("sub")

        if not user_id or not ObjectId.is_valid(user_id):
            raise credentials_error

    except JWTError:
        raise credentials_error

    user = await users_collection.find_one(
        {"_id": ObjectId(user_id)}
    )

    if not user:
        raise credentials_error

    return user
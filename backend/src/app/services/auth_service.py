from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from fastapi import HTTPException, status
from src.app.core.config import settings
from src.app.core.security import get_password_hash, verify_password as verify_password_security, create_access_token as create_access_token_security
from src.app.db.mongo import get_database


# ---------------------------
# PASSWORD HASHING / VERIFYING
# ---------------------------

def hash_password(password: str) -> str:
    """Hash a plain password using bcrypt"""
    return get_password_hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password during login"""
    return verify_password_security(plain_password, hashed_password)


# ---------------------------
# JWT UTILITIES
# ---------------------------

def create_access_token(data: dict, expires_minutes: int = 15) -> str:
    """Generate a short-lived JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: dict, expires_days: int = 30) -> str:
    """Generate a long-lived refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=expires_days)
    to_encode.update({"exp": expire})

    # Use the same secret key for refresh tokens (can be changed to a separate key if needed)
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str, refresh: bool = False) -> dict:
    """Decode a JWT token (access or refresh)"""
    # Both use the same secret key
    secret = settings.SECRET_KEY
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------------------
# REFRESH TOKEN ROTATION
# ---------------------------

async def rotate_refresh_token(db, old_refresh_token: str):
    """
    Implements secure refresh-token rotation:
    - verifies token
    - checks DB to ensure token has not been reused
    - issues new access + refresh tokens
    - updates refresh token in DB
    """

    # Decode refresh token
    try:
        payload = decode_token(old_refresh_token, refresh=True)
    except:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token payload")

    # Fetch user from DB
    from bson import ObjectId
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Check if refresh token matches latest in DB (to prevent token reuse attacks)
    stored_refresh = user.get("refresh_token")
    if stored_refresh != old_refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token reuse detected")

    # Generate new tokens
    # Use the security module's create_access_token for consistency
    from src.app.core.security import create_access_token
    new_access = create_access_token({"sub": user_id})
    new_refresh = create_refresh_token({"sub": user_id})

    # Save rotated refresh token
    from bson import ObjectId
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"refresh_token": new_refresh}}
    )

    return new_access, new_refresh


# ---------------------------
# CREATE USER DOC
# ---------------------------

async def create_user(db, user_data):
    """Creates a new user and stores hashed password"""
    hashed_pw = hash_password(user_data.password)

    user_doc = {
        "email": user_data.email,
        "hashed_password": hashed_pw,
        "name": user_data.name,
        "role": "admin",
        "org_id": None,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "refresh_token": None
    }

    result = await db.users.insert_one(user_doc)
    return str(result.inserted_id)

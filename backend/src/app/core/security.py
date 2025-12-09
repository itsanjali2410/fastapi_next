from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
import bcrypt
from src.app.core.config import settings

# Bcrypt has a 72 byte limit, so we'll hash longer passwords first
def get_password_hash(password: str) -> str:
    """Hash password using bcrypt. Passwords longer than 72 bytes are hashed first."""
    # Convert to bytes if string
    if isinstance(password, str):
        password_bytes = password.encode('utf-8')
    else:
        password_bytes = password
    
    # If password is longer than 72 bytes, hash it first with SHA256
    if len(password_bytes) > 72:
        import hashlib
        password_bytes = hashlib.sha256(password_bytes).digest()
    
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    # Convert to bytes if string
    if isinstance(plain_password, str):
        password_bytes = plain_password.encode('utf-8')
    else:
        password_bytes = plain_password
    
    # If password is longer than 72 bytes, hash it first
    if len(password_bytes) > 72:
        import hashlib
        password_bytes = hashlib.sha256(password_bytes).digest()
    
    # Verify
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # 'sub' is the Subject (the User ID) and 'exp' is the expiration time
    to_encode.update({"exp": expire, "sub": data.get("sub")})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
import database
import secrets

import os

# Retrieve or generate JWT secret key to persist across server restarts
JWT_SECRET = os.environ.get("JWT_SECRET") or database.get_setting("jwt_secret")
if not JWT_SECRET:
    JWT_SECRET = secrets.token_hex(32)
    database.set_setting("jwt_secret", JWT_SECRET)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return payload
    except JWTError:
        return None

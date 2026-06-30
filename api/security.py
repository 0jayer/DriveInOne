import os
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_token(data: dict) -> str:
    """
    Create a signed JWT containing the given data plus an expiry time.
    'data' should include at minimum {"sub": user_id, "username": username}.
    """
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Verify and decode a JWT. Raises jwt.ExpiredSignatureError if expired,
    jwt.InvalidTokenError if tampered with or otherwise invalid.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
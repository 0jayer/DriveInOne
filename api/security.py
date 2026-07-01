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


def create_token(data: dict, expires_in_minutes: int = None, purpose: str = "access") -> str:
    """
    Create a signed JWT containing the given data plus an expiry time and a purpose claim.
    'data' should include at minimum {"sub": user_id, ...}.
    """
    payload = data.copy()
    payload["purpose"] = purpose
    expiry = (
        timedelta(minutes=expires_in_minutes)
        if expires_in_minutes is not None
        else timedelta(hours=TOKEN_EXPIRY_HOURS)
    )
    payload["exp"] = datetime.now(timezone.utc) + expiry
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Verify and decode a JWT. Raises jwt.ExpiredSignatureError if expired,
    jwt.InvalidTokenError if tampered with or otherwise invalid.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def create_state_token(user_id: int) -> str:
    """Short-lived token carrying user identity through an OAuth redirect."""
    return create_token({"sub": str(user_id)}, expires_in_minutes=10, purpose="oauth_link")


def decode_state_token(token: str) -> int:
    """Verify an OAuth state token and return the user_id it was issued for."""
    payload = decode_token(token)
    if payload.get("purpose") != "oauth_link":
        raise jwt.InvalidTokenError("Token is not a valid OAuth state token")
    return int(payload["sub"])
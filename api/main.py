from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
from database.db import Database
from database.users import get_or_create_user, create_user, get_user_by_username
from database.files import get_files_for_user
from api.security import hash_password, verify_password, create_token, decode_token

app = FastAPI(title="DriveInOne API")
bearer_scheme = HTTPBearer()


# --- Auth dependency ---

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """
    Runs before any endpoint that declares it as a dependency.
    Decodes the JWT from the Authorization header and returns the user payload.
    Raises 401 if the token is missing, expired, or tampered with.
    """
    try:
        payload = decode_token(credentials.credentials)
        return {"user_id": int(payload["sub"]), "username": payload["username"]}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired — please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# --- Request body models ---

class SignupRequest(BaseModel):
    username: str
    password: str
    display_name: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


# --- Endpoints ---

@app.get("/")
def root():
    return {"status": "DriveInOne API is running"}


@app.post("/signup", status_code=201)
def signup(body: SignupRequest):
    """
    Create a new user account with a hashed password.
    Returns the new user's id and username.
    """
    conn = Database.get_instance()
    try:
        hashed = hash_password(body.password)
        user_id = create_user(
            conn,
            username=body.username,
            hashed_password=hashed,
            display_name=body.display_name or body.username,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return {"user_id": user_id, "username": body.username}


@app.post("/login")
def login(body: LoginRequest):
    """
    Verify username + password. Returns a JWT token on success.
    """
    conn = Database.get_instance()
    row = get_user_by_username(conn, body.username)

    if not row:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user_id, username, display_name, password_hash = row

    if not password_hash:
        raise HTTPException(status_code=401, detail="This account has no password set — use the CLI")

    if not verify_password(body.password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token({"sub": str(user_id), "username": username})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/files")
def list_files(current_user: dict = Depends(get_current_user)):
    """
    Returns all files belonging to the authenticated user.
    Requires a valid Bearer token in the Authorization header.
    """
    conn = Database.get_instance()
    rows = get_files_for_user(conn, current_user["user_id"])

    files = [
        {
            "file_id": row[0],
            "filename": row[1],
            "size_bytes": row[2],
            "total_chunks": row[3],
            "uploaded_at": row[4],
        }
        for row in rows
    ]

    return {"username": current_user["username"], "user_id": current_user["user_id"], "files": files}
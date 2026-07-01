import mimetypes
import os
import tempfile
import jwt
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from database.db import Database
from database.users import get_or_create_user, create_user, get_user_by_username
from database.files import get_files_for_user
from database.providers import register_provider
from api.security import (
    hash_password, verify_password, create_token, decode_token,
    create_state_token, decode_state_token,
)
from api.providers import load_providers
from distribution.upload import DistributionUpload
from distribution.download import DistributionDownload
from providers.gdrive import GoogleDriveProvider
from providers.dropbox import DropboxProvider
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from urllib.parse import quote

app = FastAPI(title="DriveInOne API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # dev only — restrict to your real frontend origin before deploying
    allow_credentials=False,   # JWT goes in the Authorization header, not cookies, so this can stay False
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

bearer_scheme = HTTPBearer()


FRONTEND_URL = "http://127.0.0.1:5500"
# --- OAuth config ---
GOOGLE_CREDENTIALS_PATH = "credentials/google_credentials.json"          # Desktop client — CLI (setup.py) only
GOOGLE_WEB_CREDENTIALS_PATH = "credentials/google_credentials_web.json"  # Web client — API redirect flow
GOOGLE_REDIRECT_URI = "http://127.0.0.1:8000/accounts/gdrive/callback"
DROPBOX_REDIRECT_URI = "http://127.0.0.1:8000/accounts/dropbox/callback"


# --- Auth dependency ---

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("purpose") != "access":
            raise jwt.InvalidTokenError("Token is not a valid access token")
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


# --- Core endpoints ---

@app.get("/")
def root():
    return {"status": "DriveInOne API is running"}


@app.post("/signup", status_code=201)
def signup(body: SignupRequest):
    """Create a new user account. Returns user_id and username."""
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
    """Verify credentials. Returns a JWT access token."""
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
    """List all files belonging to the authenticated user."""
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


@app.get("/files/{file_id}/download")
def download_file(file_id: int, current_user: dict = Depends(get_current_user)):
    """Reassemble and return a file owned by the authenticated user."""
    conn = Database.get_instance()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT original_filename, total_size_bytes FROM files WHERE file_id = %s AND user_id = %s",
        (file_id, current_user["user_id"]),
    )
    row = cursor.fetchone()
    if not row or not isinstance(row, (tuple, list)) or len(row) < 2:
        raise HTTPException(status_code=404, detail="File not found")

    filename = row[0]
    total_size_bytes = row[1]
    media_type, _ = mimetypes.guess_type(filename)
    if not media_type:
        media_type = "application/octet-stream"

    def iter_file_bytes():
        downloader = DistributionDownload()
        for chunk in downloader.iter_download_bytes(file_id):
            yield chunk

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"; filename*=UTF-8\'\'{quote(filename)}',
        "Cache-Control": "no-store",
    }
    if total_size_bytes is not None:
        headers["Content-Length"] = str(total_size_bytes)

    try:
        return StreamingResponse(
            iter_file_bytes(),
            media_type=media_type,
            headers=headers,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/upload", status_code=201)
def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a file, distributing it across the user's registered providers.
    Returns file metadata including file_id and how many chunks were created.
    """
    conn = Database.get_instance()

    providers = load_providers(conn, current_user["user_id"])
    if not providers:
        raise HTTPException(
            status_code=400,
            detail="No storage providers registered. Add a provider first."
        )

    safe_filename = os.path.basename(file.filename) if file.filename else "upload"
    suffix = os.path.splitext(safe_filename)[1]
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            content = file.file.read()
            tmp.write(content)


        dist = DistributionUpload(tmp_path, providers, original_filename=safe_filename)
        
        try:
            allocations = dist.allocate()
        except ValueError:
            raise HTTPException(
                status_code=507,
                detail="Not enough free space across your providers to store this file."
            )

        dist.upload(allocations, owner=current_user["user_id"])
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    rows = get_files_for_user(conn, current_user["user_id"])
    latest = rows[0] if rows else None
    return {
        "message": f"'{safe_filename}' uploaded successfully",
        "file_id": latest[0] if latest else None,
        "filename": safe_filename,
        "size_bytes": len(content),
        "chunks": len(allocations),
    }

@app.get("/accounts")
def list_accounts(current_user: dict = Depends(get_current_user)):
    """List the authenticated user's connected storage providers with live capacity."""
    conn = Database.get_instance()
    providers = load_providers(conn, current_user["user_id"])
    return {
        "providers": [
            {
                "provider_id": p["provider_id"],
                "provider_type": p["name"],
                "account_email": p["account_email"],
                "total_space_bytes": p["total_space"],
                "used_space_bytes": p["used_space"],
            }
            for p in providers
        ]
    }


# --- Google Drive linking ---

@app.get("/accounts/gdrive/authorize")
def gdrive_authorize(current_user: dict = Depends(get_current_user)):
    """Returns a Google consent URL. Frontend redirects the user's browser to it."""
    state = create_state_token(current_user["user_id"])
    url = GoogleDriveProvider.get_authorization_url(
        GOOGLE_WEB_CREDENTIALS_PATH, GOOGLE_REDIRECT_URI, state
    )
    return {"authorization_url": url}


@app.get("/accounts/gdrive/callback")
def gdrive_callback(code: str, state: str):
    try:
        user_id = decode_state_token(state)
    except jwt.PyJWTError:
        return RedirectResponse(url=f"{FRONTEND_URL}/index.html?expired=1")

    access_token, refresh_token = GoogleDriveProvider.exchange_code(
        GOOGLE_WEB_CREDENTIALS_PATH, GOOGLE_REDIRECT_URI, code
    )
    provider = GoogleDriveProvider(
        GOOGLE_WEB_CREDENTIALS_PATH, token=access_token, refresh_token=refresh_token
    )
    email = provider.get_account_email()
    total, used = provider.get_total_space()

    conn = Database.get_instance()
    register_provider(
        conn, user_id, "gdrive", email, email, total, used,
        "https://drive.google.com", access_token, refresh_token
    )

    return RedirectResponse(url=f"{FRONTEND_URL}/dashboard.html?connected=gdrive")



# --- Dropbox linking ---

@app.get("/accounts/dropbox/authorize")
def dropbox_authorize(current_user: dict = Depends(get_current_user)):
    state = create_state_token(current_user["user_id"])
    url = DropboxProvider.get_authorization_url(DROPBOX_REDIRECT_URI, state)
    return {"authorization_url": url}


@app.get("/accounts/dropbox/callback")
def dropbox_callback(code: str, state: str):
    try:
        user_id = decode_state_token(state)
    except jwt.PyJWTError:
        return RedirectResponse(url=f"{FRONTEND_URL}/index.html?expired=1")

    access_token, refresh_token = DropboxProvider.exchange_code(DROPBOX_REDIRECT_URI, code)
    provider = DropboxProvider(token=access_token, refresh_token=refresh_token)
    email = provider.get_account_email()
    total, used = provider.get_total_space()

    conn = Database.get_instance()
    register_provider(
        conn, user_id, "dropbox", email, email, total, used,
        "https://dropbox.com", access_token, refresh_token
    )

    return RedirectResponse(url=f"{FRONTEND_URL}/dashboard.html?connected=dropbox")
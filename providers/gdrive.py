from providers.base import StorageProvider
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload
from google_auth_oauthlib.flow import Flow 
import json
import io
import os


class GoogleDriveProvider(StorageProvider):
    SCOPES = ["https://www.googleapis.com/auth/drive"]

    def __init__(self, credentials_path, token=None, refresh_token=None):
        super().__init__(bucket="gdrive", region="global")
        self._credentials_path = credentials_path
        self._service = None
        self._creds = None

        if token and refresh_token:
            self._load_from_tokens(token, refresh_token)
        else:
            self._run_oauth_flow()

        self._service = build("drive", "v3", credentials=self._creds)
        print("[GoogleDrive] Authenticated successfully")

    def _client_config(self):
        """Read client_id/secret out of the credentials file (app-level, never changes)."""
        with open(self._credentials_path, "r") as f:
            data = json.load(f)
        # works whether the file uses "installed" or "web" key
        key = "installed" if "installed" in data else "web"
        return data[key]["client_id"], data[key]["client_secret"]

    def _load_from_tokens(self, token, refresh_token):
        client_id, client_secret = self._client_config()
        self._creds = Credentials(
            token=token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=self.SCOPES,
        )
        if not self._creds.valid:
            self._creds.refresh(Request())
            print("[GoogleDrive] Access token refreshed")

    def _run_oauth_flow(self):
        flow = InstalledAppFlow.from_client_secrets_file(
            self._credentials_path, self.SCOPES
        )
        self._creds = flow.run_local_server(port=0)

    def get_tokens(self):
        """Return (access_token, refresh_token) after auth — for saving to DB."""
        return self._creds.token, self._creds.refresh_token

    def upload_file(self, file_path, remote_key):
        file_metadata = {"name": remote_key}
        media = MediaFileUpload(file_path, resumable=True)
        file = self._service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name, size"
        ).execute()
        print(f"[GoogleDrive] Uploaded {file_path} → {file['name']} (id: {file['id']})")
        return file

    def upload_bytes(self, data: bytes, remote_key: str):
        file_metadata = {"name": remote_key}
        media = MediaIoBaseUpload(io.BytesIO(data), mimetype="application/octet-stream", resumable=True)
        file = self._service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name"
        ).execute()
        print(f"[GoogleDrive] Uploaded chunk → {file['name']} (id: {file['id']})")
        return file

    def download_file(self, remote_key, local_path):
        results = self._service.files().list(
            q=f"name='{remote_key}'",
            fields="files(id, name)"
        ).execute()
        files = results.get("files", [])
        if not files:
            raise FileNotFoundError(f"File '{remote_key}' not found in Google Drive")

        file_id = files[0]["id"]
        request = self._service.files().get_media(fileId=file_id)

        with open(local_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

        print(f"[GoogleDrive] Downloaded '{remote_key}' → {local_path}")

    def download_bytes(self, remote_key: str) -> bytes:
        results = self._service.files().list(
            q=f"name='{remote_key}'",
            fields="files(id, name)"
        ).execute()
        files = results.get("files", [])
        if not files:
            raise FileNotFoundError(f"Chunk '{remote_key}' not found in Google Drive")

        file_id = files[0]["id"]
        request = self._service.files().get_media(fileId=file_id)

        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        print(f"[GoogleDrive] Downloaded chunk '{remote_key}' ({buffer.tell()} bytes)")
        return buffer.getvalue()

    def delete_file(self, remote_key):
        results = self._service.files().list(
            q=f"name='{remote_key}'",
            fields="files(id, name)"
        ).execute()
        files = results.get("files", [])
        if files:
            self._service.files().delete(fileId=files[0]["id"]).execute()
            print(f"[GoogleDrive] Deleted '{remote_key}'")
        else:
            raise FileNotFoundError(f"File '{remote_key}' not found in Google Drive")

    def list_files(self, folder_id="root"):
        results = self._service.files().list(
            q=f"'{folder_id}' in parents",
            fields="files(id, name, size, mimeType)"
        ).execute()
        files = results.get("files", [])
        for file in files:
            print(f"{file['name']} ({file.get('size', 'N/A')} bytes)")
        return files

    def get_account_email(self) -> str:
        about = self._service.about().get(fields="user").execute()
        return about["user"]["emailAddress"]

    def get_total_space(self) -> tuple[int, int]:
        about = self._service.about().get(fields="storageQuota").execute()
        quota = about["storageQuota"]
        total = int(quota["limit"])
        used = int(quota["usage"])
        return total, used

    def get_free_space(self) -> int:
        total, used = self.get_total_space()
        return total - used
    
    @staticmethod
    def get_authorization_url(credentials_path, redirect_uri, state):
        flow = Flow.from_client_secrets_file(
            credentials_path, scopes=GoogleDriveProvider.SCOPES, redirect_uri=redirect_uri,
            autogenerate_code_verifier=False,   # ← add this
        )
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",
            state=state,
        )
        return auth_url

    @staticmethod
    def exchange_code(credentials_path, redirect_uri, code):
        flow = Flow.from_client_secrets_file(
            credentials_path, scopes=GoogleDriveProvider.SCOPES, redirect_uri=redirect_uri
        )
        flow.fetch_token(code=code)
        creds = flow.credentials
        return creds.token, creds.refresh_token
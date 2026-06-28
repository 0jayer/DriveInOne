from providers.base import StorageProvider
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os

class GoogleDriveProvider(StorageProvider):
    def __init__(self, credentials_path):
        super().__init__(bucket="gdrive", region="global")
        self._credentials_path = credentials_path
        self._service = None  # will hold the authenticated Drive API client
        
    def upload_file(self, file_path, remote_key):
        print(f"[GoogleDrive] Uploading {file_path} to {remote_key}")

    def download_file(self, file_path, remote_key):
        print(f"[GoogleDrive] Downloading {remote_key} to {file_path}")

    def delete_file(self, remote_key):
        print(f"[GoogleDrive] Deleting {remote_key}")


    def authenticate(self):
        SCOPES = ["https://www.googleapis.com/auth/drive"]
        token_path = "credentials/token.json"

        creds = None
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(
                self._credentials_path, SCOPES
            )
            creds = flow.run_local_server(port=0)
            with open(token_path, "w") as token:
                token.write(creds.to_json())

        self._service = build("drive", "v3", credentials=creds)
        print("[GoogleDrive] Authenticated successfully")
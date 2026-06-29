from providers.base import StorageProvider
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.http import MediaIoBaseDownload
import os

class GoogleDriveProvider(StorageProvider):
    def __init__(self, credentials_path):
        super().__init__(bucket="gdrive", region="global")
        self._credentials_path = credentials_path
        self._service = None  # will hold the authenticated Drive API client
        

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


    def list_files(self, folder_id="root"):
        results = self._service.files().list(
            q=f"'{folder_id}' in parents",
            fields="files(id, name, size, mimeType)"
        ).execute()
        files = results.get("files", [])
        for file in files:
            print(f"{file['name']} ({file.get('size', 'N/A')} bytes)")
        return files
    
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
    
    def download_file(self, remote_key, local_path):
        
        # find file by name
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
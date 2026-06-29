from providers.base import StorageProvider
import dropbox
import os
from dotenv import load_dotenv

load_dotenv()

class DropboxProvider(StorageProvider):
    def __init__(self):
        super().__init__(bucket="dropbox", region="global")
        self._client = dropbox.Dropbox(os.getenv("DROPBOX_ACCESS_TOKEN"))

    def upload_file(self, file_path, remote_key):
        with open(file_path, "rb") as f:
            self._client.files_upload(f.read(), f"/{remote_key}")
        print(f"[Dropbox] Uploaded {file_path} → /{remote_key}")

    def download_file(self, remote_key, local_path):
        self._client.files_download_to_file(local_path, f"/{remote_key}")
        print(f"[Dropbox] Downloaded /{remote_key} → {local_path}")

    def list_files(self, path=""):
        result = self._client.files_list_folder(path)
        files = []
        for entry in result.entries:
            if hasattr(entry, 'size'):
                print(f"{entry.name} ({entry.size} bytes)")
                files.append({"name": entry.name, "size": entry.size, "id": entry.id})
            else:
                print(f"{entry.name} (folder)")
                files.append({"name": entry.name, "id": entry.id})
        return files

    def delete_file(self, remote_key):
        self._client.files_delete_v2(f"/{remote_key}")
        print(f"[Dropbox] Deleted /{remote_key}")
        
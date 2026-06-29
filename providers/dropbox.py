from providers.base import StorageProvider
import dropbox
from dropbox import DropboxOAuth2FlowNoRedirect
import os
from dotenv import load_dotenv

load_dotenv()


class DropboxProvider(StorageProvider):
    def __init__(self, token=None, refresh_token=None):
        super().__init__(bucket="dropbox", region="global")
        self._app_key = os.getenv("DROPBOX_APP_KEY")
        self._app_secret = os.getenv("DROPBOX_APP_SECRET")
        self._client = None

        if token and refresh_token:
            # Load from DB tokens
            self._client = dropbox.Dropbox(
                oauth2_access_token=token,
                oauth2_refresh_token=refresh_token,
                app_key=self._app_key,
                app_secret=self._app_secret,
            )
        else:
            # Run OAuth flow
            self._client = self._run_oauth_flow()

    def _run_oauth_flow(self):
        auth_flow = DropboxOAuth2FlowNoRedirect(
            self._app_key,
            self._app_secret,
            token_access_type="offline"  # offline = gets refresh token
        )

        authorize_url = auth_flow.start()
        print(f"\n[Dropbox] Visit this URL to authorize:\n{authorize_url}\n")
        auth_code = input("Enter the authorization code here: ").strip()

        oauth_result = auth_flow.finish(auth_code)

        # Save tokens to .env temporarily so setup.py can read them
        # In the web app these go straight to DB
        self._access_token = oauth_result.access_token
        self._refresh_token = oauth_result.refresh_token

        return dropbox.Dropbox(
            oauth2_access_token=oauth_result.access_token,
            oauth2_refresh_token=oauth_result.refresh_token,
            app_key=self._app_key,
            app_secret=self._app_secret,
        )

    def get_tokens(self):
        """Return tokens after OAuth flow for saving to DB"""
        return self._access_token, self._refresh_token

    def upload_file(self, file_path, remote_key):
        with open(file_path, "rb") as f:
            self._client.files_upload(f.read(), f"/{remote_key}")
        print(f"[Dropbox] Uploaded {file_path} → /{remote_key}")

    def upload_bytes(self, data: bytes, remote_key: str):
        self._client.files_upload(data, f"/{remote_key}")
        print(f"[Dropbox] Uploaded chunk → /{remote_key}")

    def download_file(self, remote_key, local_path):
        self._client.files_download_to_file(local_path, f"/{remote_key}")
        print(f"[Dropbox] Downloaded /{remote_key} → {local_path}")

    def download_bytes(self, remote_key: str) -> bytes:
        _, response = self._client.files_download(f"/{remote_key}")
        print(f"[Dropbox] Downloaded chunk '/{remote_key}' ({len(response.content)} bytes)")
        return response.content

    def delete_file(self, remote_key):
        self._client.files_delete_v2(f"/{remote_key}")
        print(f"[Dropbox] Deleted /{remote_key}")

    def list_files(self, path=""):
        result = self._client.files_list_folder(path)
        files = []
        for entry in result.entries:
            if hasattr(entry, "size"):
                print(f"{entry.name} ({entry.size} bytes)")
                files.append({"name": entry.name, "size": entry.size, "id": entry.id})
            else:
                print(f"{entry.name} (folder)")
                files.append({"name": entry.name, "id": entry.id})
        return files

    def get_account_email(self) -> str:
        account = self._client.users_get_current_account()
        return account.email

    def get_total_space(self) -> tuple[int, int]:
        usage = self._client.users_get_space_usage()
        allocated = usage.allocation.get_individual().allocated
        used = usage.used
        return allocated, used

    def get_free_space(self) -> int:
        total, used = self.get_total_space()
        return total - used
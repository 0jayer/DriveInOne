from providers.base import StorageProvider

class GCSProvider(StorageProvider):
    def __init__(self, bucket, region, service_account):
        super().__init__(bucket, region)
        self._service_account = service_account
        
    def upload_file(self, file_path, remote_key):
        # Implement GCS file upload logic here
        print(f"[GCS] Uploading {file_path} to {remote_key}")

    def download_file(self, file_path, remote_key):
        # Implement GCS file download logic here
        print(f"[GCS] Downloading {remote_key} to {file_path}")
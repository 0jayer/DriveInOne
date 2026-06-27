from abc import  ABC, abstractmethod


class StorageProvider(ABC):
    def __init__(self, bucket, region):
        self._bucket = bucket
        self._region = region


    def __repr__(self):
        return f"StorageProvider(bucket={self._bucket!r}, region={self._region!r})"
    
    def __str__(self):
        return f"StorageProvider(bucket={self._bucket})"

    @abstractmethod
    def upload_file(self, file_path, remote_key):
        """Upload file to the storage provider"""
        pass
    
    @abstractmethod
    def download_file(self, file_path, remote_key):
        """Download file from the storage provider"""
        pass

    @abstractmethod
    def delete_file(self, remote_key):
        """Delete file from the storage provider"""
        pass
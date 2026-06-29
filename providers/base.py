from abc import ABC, abstractmethod


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
        """Upload a whole file to the storage provider"""
        pass

    @abstractmethod
    def upload_bytes(self, data: bytes, remote_key: str):
        """Upload raw bytes (a chunk) to the storage provider"""
        pass

    @abstractmethod
    def download_file(self, remote_key, local_path):
        """Download file from the storage provider to disk"""
        pass

    @abstractmethod
    def download_bytes(self, remote_key: str) -> bytes:
        """Download a chunk from the storage provider, return raw bytes"""
        pass

    @abstractmethod
    def delete_file(self, remote_key):
        """Delete file from the storage provider"""
        pass
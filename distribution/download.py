import hashlib
import os
from database.db import Database
from database.files import get_files_for_user, get_file_metadata, get_chunks_for_file
from providers.gdrive import GoogleDriveProvider
from providers.dropbox import DropboxProvider


class DistributionDownload:
    def __init__(self):
        self._conn = Database.get_instance()
        self._provider_cache = {}

    def _load_provider(self, provider_id):
        if provider_id in self._provider_cache:
            return self._provider_cache[provider_id]

        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT provider_type, token, refresh_token FROM providers WHERE provider_id = %s",
            (provider_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Provider {provider_id} not found in DB")

        provider_type, token, refresh_token = row

        if provider_type == "gdrive":
            instance = GoogleDriveProvider("credentials/google_credentials.json", token=token, refresh_token=refresh_token)
        elif provider_type == "dropbox":
            instance = DropboxProvider(token=token, refresh_token=refresh_token)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

        self._provider_cache[provider_id] = instance
        return instance

    def list_files(self, user_id):
        rows = get_files_for_user(self._conn, user_id)
        if not rows:
            print("[Download] No files found for this user.")
            return []
        print("\n[Files in DriveInOne]")
        print(f"  {'ID':<6} {'Name':<30} {'Size (B)':>12} {'Chunks':>7}  Uploaded")
        print("  " + "-" * 68)
        for file_id, name, size, chunks, uploaded_at in rows:
            print(f"  {file_id:<6} {name:<30} {size:>12} {chunks:>7}  {uploaded_at[:19]}")
        return rows

    def download(self, file_id, output_dir="."):
        row = get_file_metadata(self._conn, file_id)
        if not row:
            raise FileNotFoundError(f"No file with file_id={file_id} in DB")

        filename, total_size, total_chunks, expected_checksum = row
        print(f"\n[Download] '{filename}' — {total_size} bytes across {total_chunks} chunk(s)")

        chunks = get_chunks_for_file(self._conn, file_id)

        if len(chunks) != total_chunks:
            raise ValueError(
                f"DB inconsistency: expected {total_chunks} chunks, found {len(chunks)}"
            )

        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)

        with open(output_path, "wb") as out_file:
            for chunk_index, provider_id, remote_key, chunk_size, expected_chunk_checksum in chunks:
                provider = self._load_provider(provider_id)
                data = provider.download_bytes(remote_key)

                actual_checksum = hashlib.sha256(data).hexdigest()
                if actual_checksum != expected_chunk_checksum:
                    raise ValueError(
                        f"Chunk {chunk_index} checksum mismatch — data may be corrupted"
                    )

                out_file.write(data)
                print(f"[Download] Chunk {chunk_index}: {len(data)} bytes ✓")

        actual_file_checksum = self._file_checksum(output_path)
        if actual_file_checksum != expected_checksum:
            os.remove(output_path)
            raise ValueError(
                "Final file checksum mismatch — file deleted. Upload may have been corrupted."
            )

        print(f"[Download] '{filename}' reassembled at '{output_path}' ✓")
        return output_path

    def _file_checksum(self, path):
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                sha256.update(block)
        return sha256.hexdigest()
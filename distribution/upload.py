import threading
import hashlib
import os
import datetime
from database.db import Database


class DistributionUpload:
    def __init__(self, file_path, providers):
        self.file_path = file_path
        self.file_size = os.path.getsize(file_path)
        self.providers = providers
        self._lock = threading.Lock()
        self._results = []

    def allocate(self):
        sorted_providers = sorted(self.providers, key=lambda p: p["free_space"], reverse=True)

        total_free_space = sum(p["free_space"] for p in sorted_providers)
        if total_free_space < self.file_size:
            raise ValueError("Not enough free space available")

        allocations = []
        remaining_size = self.file_size
        offset = 0
        for chunk_index, provider in enumerate(sorted_providers):
            if remaining_size <= 0:
                break
            allocated_size = min(remaining_size, provider["free_space"])
            allocations.append((provider, allocated_size, offset, chunk_index))
            remaining_size -= allocated_size
            offset = self.file_size - remaining_size

        return allocations

    def upload(self, allocations, owner="default", virtual_path=None):
        self._results = []
        threads = []
        total_chunks = len(allocations)          # add this
        for provider, size, offset, chunk_index in allocations:
            t = threading.Thread(
                target=self._upload_chunk,
                args=(provider, size, offset, chunk_index, total_chunks)   # pass it down
            )
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

        self._record_to_db(owner, virtual_path)

    def _upload_chunk(self, provider, size, offset, chunk_index, total_chunks):
        filename = os.path.basename(self.file_path)
        
        # use original filename if no splitting needed, chunk name if split
        if total_chunks == 1:
            remote_key = filename
        else:
            remote_key = f"{filename}_chunk_{chunk_index}"

        with open(self.file_path, "rb") as f:
            f.seek(offset)
            data = f.read(size)

        checksum = hashlib.sha256(data).hexdigest()
        provider["instance"].upload_bytes(data, remote_key)

        with self._lock:
            self._results.append({
                "chunk_index": chunk_index,
                "provider_id": provider["provider_id"],
                "remote_key": remote_key,
                "chunk_size_bytes": size,
                "checksum_chunk": checksum,
            })

        print(f"[Upload] Chunk {chunk_index}: {size} bytes → {provider['name']} as '{remote_key}'")
    def _file_checksum(self):
        sha256 = hashlib.sha256()
        with open(self.file_path, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                sha256.update(block)
        return sha256.hexdigest()

    def _record_to_db(self, owner, virtual_path):
        filename = os.path.basename(self.file_path)
        file_ext = os.path.splitext(filename)[1] or "unknown"
        virtual_path = virtual_path or f"/{filename}"
        total_chunks = len(self._results)
        file_checksum = self._file_checksum()

        # chunk_index 0 is always the first/primary provider
        primary = next(r for r in self._results if r["chunk_index"] == 0)
        primary_provider_id = primary["provider_id"]

        conn = Database.get_instance()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO files (
                original_filename, file_type, total_size_bytes, total_chunks,
                virtual_path, uploaded_at, checksum_file, owner, uploaded_provider_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING file_id
        """, (
            filename, file_ext, self.file_size, total_chunks,
            virtual_path, datetime.datetime.utcnow().isoformat(),
            file_checksum, owner, primary_provider_id
        ))

        file_id = cursor.fetchone()[0]

        for result in sorted(self._results, key=lambda r: r["chunk_index"]):
            cursor.execute("""
                INSERT INTO chunks (
                    file_id, chunk_index, chunk_size_bytes,
                    remote_key, checksum_chunk, provider_id
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                file_id,
                result["chunk_index"],
                result["chunk_size_bytes"],
                result["remote_key"],
                result["checksum_chunk"],
                result["provider_id"],
            ))

        conn.commit()
        print(f"[DB] Recorded '{filename}' (file_id={file_id}) with {total_chunks} chunk(s)")
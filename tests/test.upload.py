import os
import hashlib
import tempfile
import pytest
from unittest.mock import MagicMock
from distribution.upload import DistributionUpload


def make_temp_file(content: bytes) -> str:
    f = tempfile.NamedTemporaryFile(delete=False)
    f.write(content)
    f.close()
    return f.name


def make_mock_provider(provider_id: int, free_space: int, name: str) -> dict:
    return {
        "name": name,
        "free_space": free_space,
        "provider_id": provider_id,
        "instance": MagicMock(),
    }


def patch_db(mocker, file_id=1):
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.fetchone.return_value = [file_id]
    mocker.patch("distribution.upload.Database.get_instance", return_value=mock_conn)
    return mock_conn


class TestRemoteKeyNaming:
    def test_single_chunk_uses_original_filename(self, mocker):
        content = b"hello world"
        tmp = make_temp_file(content)
        try:
            provider = make_mock_provider(1, 1000, "gdrive")
            dist = DistributionUpload(tmp, [provider])
            patch_db(mocker)

            dist.upload(dist.allocate())

            remote_key = provider["instance"].upload_bytes.call_args[0][1]
            assert remote_key == os.path.basename(tmp)
            assert "_chunk_" not in remote_key
        finally:
            os.unlink(tmp)

    def test_multi_chunk_uses_chunk_suffix(self, mocker):
        content = b"x" * 300
        tmp = make_temp_file(content)
        try:
            p1 = make_mock_provider(1, 200, "gdrive")
            p2 = make_mock_provider(2, 200, "dropbox")
            dist = DistributionUpload(tmp, [p1, p2])
            patch_db(mocker)

            dist.upload(dist.allocate())

            all_calls = (
                p1["instance"].upload_bytes.call_args_list +
                p2["instance"].upload_bytes.call_args_list
            )
            remote_keys = [call[0][1] for call in all_calls]
            assert all("_chunk_" in key for key in remote_keys)
        finally:
            os.unlink(tmp)

    def test_multi_chunk_keys_contain_chunk_index(self, mocker):
        content = b"x" * 300
        tmp = make_temp_file(content)
        try:
            p1 = make_mock_provider(1, 200, "gdrive")
            p2 = make_mock_provider(2, 200, "dropbox")
            dist = DistributionUpload(tmp, [p1, p2])
            patch_db(mocker)

            dist.upload(dist.allocate())

            all_calls = (
                p1["instance"].upload_bytes.call_args_list +
                p2["instance"].upload_bytes.call_args_list
            )
            remote_keys = [call[0][1] for call in all_calls]
            assert any("_chunk_0" in key for key in remote_keys)
            assert any("_chunk_1" in key for key in remote_keys)
        finally:
            os.unlink(tmp)


class TestUploadBytes:
    def test_correct_bytes_sent_to_provider(self, mocker):
        content = b"exact content to upload"
        tmp = make_temp_file(content)
        try:
            provider = make_mock_provider(1, 1000, "gdrive")
            dist = DistributionUpload(tmp, [provider])
            patch_db(mocker)

            dist.upload(dist.allocate())

            uploaded = provider["instance"].upload_bytes.call_args[0][0]
            assert uploaded == content
        finally:
            os.unlink(tmp)

    def test_split_bytes_sum_to_original(self, mocker):
        content = b"y" * 300
        tmp = make_temp_file(content)
        try:
            p1 = make_mock_provider(1, 200, "gdrive")
            p2 = make_mock_provider(2, 200, "dropbox")
            dist = DistributionUpload(tmp, [p1, p2])
            patch_db(mocker)

            dist.upload(dist.allocate())

            chunk0 = p1["instance"].upload_bytes.call_args[0][0]
            chunk1 = p2["instance"].upload_bytes.call_args[0][0]
            assert len(chunk0) + len(chunk1) == 300
        finally:
            os.unlink(tmp)


class TestChecksums:
    def test_chunk_checksum_is_sha256_of_data(self, mocker):
        content = b"checksum me"
        tmp = make_temp_file(content)
        try:
            provider = make_mock_provider(1, 1000, "gdrive")
            dist = DistributionUpload(tmp, [provider])
            mock_conn = patch_db(mocker)

            dist.upload(dist.allocate())

            expected = hashlib.sha256(content).hexdigest()
            cursor = mock_conn.cursor.return_value
            chunk_insert = next(
                c for c in cursor.execute.call_args_list
                if "INSERT INTO chunks" in str(c)
            )
            chunk_args = chunk_insert[0][1]
            assert chunk_args[4] == expected  # checksum_chunk is 5th param
        finally:
            os.unlink(tmp)


class TestDatabaseWrites:
    def test_file_row_inserted_into_db(self, mocker):
        content = b"db write test"
        tmp = make_temp_file(content)
        try:
            provider = make_mock_provider(1, 1000, "gdrive")
            dist = DistributionUpload(tmp, [provider])
            mock_conn = patch_db(mocker)

            dist.upload(dist.allocate())

            cursor = mock_conn.cursor.return_value
            file_inserts = [
                c for c in cursor.execute.call_args_list
                if "INSERT INTO files" in str(c)
            ]
            assert len(file_inserts) == 1
        finally:
            os.unlink(tmp)

    def test_chunk_rows_inserted_per_allocation(self, mocker):
        content = b"z" * 300
        tmp = make_temp_file(content)
        try:
            p1 = make_mock_provider(1, 200, "gdrive")
            p2 = make_mock_provider(2, 200, "dropbox")
            dist = DistributionUpload(tmp, [p1, p2])
            mock_conn = patch_db(mocker)

            dist.upload(dist.allocate())

            cursor = mock_conn.cursor.return_value
            chunk_inserts = [
                c for c in cursor.execute.call_args_list
                if "INSERT INTO chunks" in str(c)
            ]
            assert len(chunk_inserts) == 2
        finally:
            os.unlink(tmp)
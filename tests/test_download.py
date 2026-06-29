import os
import hashlib
import pytest
from unittest.mock import MagicMock
from distribution.download import DistributionDownload


def patch_db(mocker, filename, total_size, total_chunks, file_checksum, chunks):
    mock_conn = MagicMock()
    cursor = mock_conn.cursor.return_value
    cursor.fetchone.return_value = (filename, total_size, total_chunks, file_checksum)
    cursor.fetchall.return_value = chunks
    mocker.patch("distribution.download.Database.get_instance", return_value=mock_conn)
    return mock_conn


def patch_missing_file(mocker):
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.fetchone.return_value = None
    mocker.patch("distribution.download.Database.get_instance", return_value=mock_conn)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class TestSingleChunkDownload:
    def test_file_written_to_disk(self, mocker, tmp_path):
        content = b"hello world"
        checksum = sha256(content)

        patch_db(mocker, "test.txt", len(content), 1, checksum, [
            (0, 1, "test.txt", len(content), checksum)
        ])
        downloader = DistributionDownload()
        mock_provider = MagicMock()
        mock_provider.download_bytes.return_value = content
        mocker.patch.object(downloader, "_load_provider", return_value=mock_provider)

        output = downloader.download(1, output_dir=str(tmp_path))
        assert os.path.exists(output)

    def test_file_content_matches_original(self, mocker, tmp_path):
        content = b"exact content must match"
        checksum = sha256(content)

        patch_db(mocker, "test.txt", len(content), 1, checksum, [
            (0, 1, "test.txt", len(content), checksum)
        ])
        downloader = DistributionDownload()
        mock_provider = MagicMock()
        mock_provider.download_bytes.return_value = content
        mocker.patch.object(downloader, "_load_provider", return_value=mock_provider)

        output = downloader.download(1, output_dir=str(tmp_path))
        with open(output, "rb") as f:
            assert f.read() == content


class TestMultiChunkReassembly:
    def test_two_chunks_reassembled_in_order(self, mocker, tmp_path):
        chunk0 = b"hello"
        chunk1 = b"world"
        full = chunk0 + chunk1
        file_checksum = sha256(full)

        patch_db(mocker, "test.txt", len(full), 2, file_checksum, [
            (0, 1, "test.txt_chunk_0", len(chunk0), sha256(chunk0)),
            (1, 2, "test.txt_chunk_1", len(chunk1), sha256(chunk1)),
        ])

        downloader = DistributionDownload()
        mock_p1 = MagicMock()
        mock_p1.download_bytes.return_value = chunk0
        mock_p2 = MagicMock()
        mock_p2.download_bytes.return_value = chunk1
        mocker.patch.object(
            downloader, "_load_provider",
            side_effect=lambda pid: mock_p1 if pid == 1 else mock_p2
        )

        output = downloader.download(1, output_dir=str(tmp_path))
        with open(output, "rb") as f:
            assert f.read() == full

    def test_three_chunks_reassembled_in_order(self, mocker, tmp_path):
        chunks_data = [b"aaa", b"bbb", b"ccc"]
        full = b"".join(chunks_data)
        file_checksum = sha256(full)

        db_chunks = [
            (i, i + 1, f"test.txt_chunk_{i}", len(d), sha256(d))
            for i, d in enumerate(chunks_data)
        ]
        patch_db(mocker, "test.txt", len(full), 3, file_checksum, db_chunks)

        downloader = DistributionDownload()
        mock_providers = {i + 1: MagicMock() for i in range(3)}
        for i, d in enumerate(chunks_data):
            mock_providers[i + 1].download_bytes.return_value = d
        mocker.patch.object(
            downloader, "_load_provider",
            side_effect=lambda pid: mock_providers[pid]
        )

        output = downloader.download(1, output_dir=str(tmp_path))
        with open(output, "rb") as f:
            assert f.read() == full

    def test_output_filename_matches_original(self, mocker, tmp_path):
        content = b"data"
        checksum = sha256(content)

        patch_db(mocker, "myfile.bin", len(content), 1, checksum, [
            (0, 1, "myfile.bin", len(content), checksum)
        ])
        downloader = DistributionDownload()
        mock_provider = MagicMock()
        mock_provider.download_bytes.return_value = content
        mocker.patch.object(downloader, "_load_provider", return_value=mock_provider)

        output = downloader.download(1, output_dir=str(tmp_path))
        assert os.path.basename(output) == "myfile.bin"


class TestChecksumVerification:
    def test_tampered_chunk_raises_value_error(self, mocker, tmp_path):
        real_content = b"real content"
        tampered = b"TAMPERED!!!"
        checksum = sha256(real_content)
        file_checksum = sha256(real_content)

        patch_db(mocker, "test.txt", len(real_content), 1, file_checksum, [
            (0, 1, "test.txt", len(real_content), checksum)
        ])
        downloader = DistributionDownload()
        mock_provider = MagicMock()
        mock_provider.download_bytes.return_value = tampered  # wrong data returned
        mocker.patch.object(downloader, "_load_provider", return_value=mock_provider)

        with pytest.raises(ValueError, match="checksum mismatch"):
            downloader.download(1, output_dir=str(tmp_path))

    def test_corrupt_file_deleted_after_final_checksum_failure(self, mocker, tmp_path):
        chunk0 = b"hello"
        chunk1 = b"world"
        wrong_file_checksum = sha256(b"something completely different")

        patch_db(mocker, "corrupt.txt", 10, 2, wrong_file_checksum, [
            (0, 1, "corrupt.txt_chunk_0", 5, sha256(chunk0)),
            (1, 2, "corrupt.txt_chunk_1", 5, sha256(chunk1)),
        ])
        downloader = DistributionDownload()
        mock_p1 = MagicMock()
        mock_p1.download_bytes.return_value = chunk0
        mock_p2 = MagicMock()
        mock_p2.download_bytes.return_value = chunk1
        mocker.patch.object(
            downloader, "_load_provider",
            side_effect=lambda pid: mock_p1 if pid == 1 else mock_p2
        )

        with pytest.raises(ValueError, match="Final file checksum mismatch"):
            downloader.download(1, output_dir=str(tmp_path))

        assert not os.path.exists(str(tmp_path / "corrupt.txt"))


class TestEdgeCases:
    def test_missing_file_id_raises_file_not_found(self, mocker, tmp_path):
        patch_missing_file(mocker)
        downloader = DistributionDownload()

        with pytest.raises(FileNotFoundError):
            downloader.download(999, output_dir=str(tmp_path))

    def test_chunk_count_mismatch_raises_value_error(self, mocker, tmp_path):
        content = b"hello"
        checksum = sha256(content)

        # DB says 2 chunks but only 1 is in the chunks table
        patch_db(mocker, "test.txt", len(content), 2, checksum, [
            (0, 1, "test.txt_chunk_0", len(content), checksum)
        ])
        downloader = DistributionDownload()
        mock_provider = MagicMock()
        mocker.patch.object(downloader, "_load_provider", return_value=mock_provider)

        with pytest.raises(ValueError, match="DB inconsistency"):
            downloader.download(1, output_dir=str(tmp_path))

    def test_output_directory_created_if_missing(self, mocker, tmp_path):
        content = b"data"
        checksum = sha256(content)
        new_dir = str(tmp_path / "new" / "nested" / "dir")

        patch_db(mocker, "test.txt", len(content), 1, checksum, [
            (0, 1, "test.txt", len(content), checksum)
        ])
        downloader = DistributionDownload()
        mock_provider = MagicMock()
        mock_provider.download_bytes.return_value = content
        mocker.patch.object(downloader, "_load_provider", return_value=mock_provider)

        downloader.download(1, output_dir=new_dir)
        assert os.path.isdir(new_dir)
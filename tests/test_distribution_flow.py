import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from distribution.download import DistributionDownload
from distribution.upload import DistributionUpload


class DistributionFlowTests(unittest.TestCase):
    def test_upload_uses_single_chunk_when_one_provider_can_hold_file(self):
        with tempfile.NamedTemporaryFile("wb", delete=False) as tmp:
            tmp.write(b"hello world")
            tmp_path = tmp.name

        try:
            provider = {
                "name": "gdrive",
                "provider_id": 7,
                "free_space": 100,
                "instance": MagicMock(),
            }
            provider["instance"].upload_bytes.return_value = {"ok": True}

            dist = DistributionUpload(tmp_path, [provider], original_filename="sample.txt")
            allocations = dist.allocate()

            with patch("distribution.upload.Database.get_instance", return_value=MagicMock()), \
                 patch("distribution.upload.insert_file", return_value=1), \
                 patch("distribution.upload.insert_chunk"):
                dist.upload(allocations, owner=1)

            self.assertEqual(len(allocations), 1)
            provider["instance"].upload_bytes.assert_called_once()
            args = provider["instance"].upload_bytes.call_args.args
            self.assertEqual(args[1], "sample.txt")
        finally:
            os.remove(tmp_path)

    def test_load_provider_uses_web_credentials_for_gdrive(self):
        with patch("distribution.download.Database.get_instance", return_value=MagicMock()):
            dist = DistributionDownload()
        with patch("distribution.download.get_provider_by_id", return_value=("gdrive", "token", "refresh")), \
             patch("distribution.download.GoogleDriveProvider") as mock_gdrive:
            dist._load_provider(7)

        mock_gdrive.assert_called_once_with(
            "credentials/google_credentials_web.json",
            token="token",
            refresh_token="refresh",
        )

    def test_download_reassembles_chunks_in_order(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("distribution.download.Database.get_instance", return_value=MagicMock()):
                dist = DistributionDownload()
            fake_chunks = [
                (0, 1, "chunk0", 3, hashlib.sha256(b"abc").hexdigest()),
                (1, 2, "chunk1", 3, hashlib.sha256(b"def").hexdigest()),
            ]

            def fake_load_provider(provider_id):
                mock_provider = MagicMock()
                mock_provider.download_bytes.side_effect = lambda remote_key: {
                    "chunk0": b"abc",
                    "chunk1": b"def",
                }[remote_key]
                return mock_provider

            expected_file_checksum = hashlib.sha256(b"abcdef").hexdigest()
            with patch.object(dist, "_load_provider", side_effect=fake_load_provider), \
                 patch("distribution.download.get_file_metadata", return_value=("merged.bin", 6, 2, expected_file_checksum)), \
                 patch("distribution.download.get_chunks_for_file", return_value=fake_chunks), \
                 patch.object(
                     DistributionDownload,
                     "_file_checksum",
                     new=lambda self, path: hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                 ):
                output_path = dist.download(99, output_dir=tmp_dir)

            self.assertTrue(Path(output_path).exists())
            self.assertEqual(Path(output_path).read_bytes(), b"abcdef")


if __name__ == "__main__":
    unittest.main()

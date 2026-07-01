import io
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from api.main import app
from api.security import create_token

client = TestClient(app)


def auth_header(user_id=5, username="test1"):
    token = create_token({"sub": str(user_id), "username": username})
    return {"Authorization": f"Bearer {token}"}


def make_mock_providers(free_space=1_000_000_000):
    mock_instance = MagicMock()
    mock_instance.get_free_space.return_value = free_space
    mock_instance.get_total_space.return_value = (2_000_000_000, 0)
    mock_instance.upload_bytes.return_value = None
    return [{
        "name": "gdrive",
        "instance": mock_instance,
        "free_space": free_space,
        "total_space": 2_000_000_000,
        "used_space": 0,
        "provider_id": 1,
    }]


def make_mock_conn(file_id=10):
    mock_conn = MagicMock()
    cursor = mock_conn.cursor.return_value
    # insert_file returns file_id, get_files_for_user returns one row
    cursor.fetchone.return_value = [file_id]
    cursor.fetchall.return_value = [
        (file_id, "test.txt", 11, 1, "2026-06-30T21:00:00")
    ]
    return mock_conn


class TestUploadEndpoint:
    def test_upload_requires_auth(self):
        resp = client.post("/upload", files={"file": ("test.txt", b"hello", "text/plain")})
        assert resp.status_code in (401, 403)

    def test_upload_success_returns_201(self):
        mock_conn = make_mock_conn()
        providers = make_mock_providers()
        with patch("database.db.Database.get_instance", return_value=mock_conn), \
             patch("api.main.load_providers", return_value=providers):
            resp = client.post(
                "/upload",
                files={"file": ("test.txt", b"hello world", "text/plain")},
                headers=auth_header(),
            )
        assert resp.status_code == 201

    def test_upload_response_contains_expected_fields(self):
        mock_conn = make_mock_conn(file_id=10)
        providers = make_mock_providers()
        with patch("database.db.Database.get_instance", return_value=mock_conn), \
             patch("api.main.load_providers", return_value=providers):
            resp = client.post(
                "/upload",
                files={"file": ("report.txt", b"some content", "text/plain")},
                headers=auth_header(),
            )
        data = resp.json()
        assert "file_id" in data
        assert "filename" in data
        assert "size_bytes" in data
        assert "chunks" in data
        assert data["filename"] == "report.txt"

    def test_upload_no_providers_returns_400(self):
        mock_conn = make_mock_conn()
        with patch("database.db.Database.get_instance", return_value=mock_conn), \
             patch("api.main.load_providers", return_value=[]):
            resp = client.post(
                "/upload",
                files={"file": ("test.txt", b"hello", "text/plain")},
                headers=auth_header(),
            )
        assert resp.status_code == 400
        assert "No storage providers" in resp.json()["detail"]

    def test_upload_insufficient_space_returns_507(self):
        mock_conn = make_mock_conn()
        # Provider has 1 byte free, file is much larger
        providers = make_mock_providers(free_space=1)
        with patch("database.db.Database.get_instance", return_value=mock_conn), \
             patch("api.main.load_providers", return_value=providers):
            resp = client.post(
                "/upload",
                files={"file": ("big.txt", b"x" * 1000, "text/plain")},
                headers=auth_header(),
            )
        assert resp.status_code == 507

    def test_upload_calls_provider_upload_bytes(self):
        mock_conn = make_mock_conn()
        providers = make_mock_providers()
        with patch("database.db.Database.get_instance", return_value=mock_conn), \
             patch("api.main.load_providers", return_value=providers):
            client.post(
                "/upload",
                files={"file": ("test.txt", b"hello world", "text/plain")},
                headers=auth_header(),
            )
        providers[0]["instance"].upload_bytes.assert_called_once()

    def test_upload_correct_bytes_sent_to_provider(self):
        mock_conn = make_mock_conn()
        providers = make_mock_providers()
        content = b"exact content check"
        with patch("database.db.Database.get_instance", return_value=mock_conn), \
             patch("api.main.load_providers", return_value=providers):
            client.post(
                "/upload",
                files={"file": ("test.txt", content, "text/plain")},
                headers=auth_header(),
            )
        uploaded_bytes = providers[0]["instance"].upload_bytes.call_args[0][0]
        assert uploaded_bytes == content
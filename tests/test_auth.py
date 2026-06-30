import pytest
import jwt
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from api.main import app
from api.security import hash_password, verify_password, create_token, decode_token

client = TestClient(app)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("mysecret")
        assert hashed != "mysecret"

    def test_correct_password_verifies(self):
        hashed = hash_password("mysecret")
        assert verify_password("mysecret", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("mysecret")
        assert verify_password("wrongpassword", hashed) is False

    def test_same_password_produces_different_hashes(self):
        # bcrypt salts every hash — same input never produces same output
        h1 = hash_password("mysecret")
        h2 = hash_password("mysecret")
        assert h1 != h2

    def test_both_hashes_still_verify(self):
        h1 = hash_password("mysecret")
        h2 = hash_password("mysecret")
        assert verify_password("mysecret", h1) is True
        assert verify_password("mysecret", h2) is True


class TestJWTTokens:
    def test_create_token_returns_string(self):
        token = create_token({"sub": "1", "username": "ahnaf"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_recovers_payload(self):
        token = create_token({"sub": "42", "username": "ahnaf"})
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert payload["username"] == "ahnaf"

    def test_tampered_token_raises(self):
        token = create_token({"sub": "1", "username": "ahnaf"})
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(jwt.InvalidTokenError):
            decode_token(tampered)

    def test_token_contains_expiry(self):
        token = create_token({"sub": "1", "username": "ahnaf"})
        payload = decode_token(token)
        assert "exp" in payload


class TestSignupEndpoint:
    def test_signup_success(self):
        mock_conn = MagicMock()
        cursor = mock_conn.cursor.return_value
        cursor.fetchone.side_effect = [None, [99]]
        with patch("database.db.Database.get_instance", return_value=mock_conn):
            resp = client.post("/signup", json={
                "username": "newuser",
                "password": "secret123",
            })
        assert resp.status_code == 201
        assert resp.json()["username"] == "newuser"
        assert "user_id" in resp.json()

    def test_signup_duplicate_username_returns_409(self):
        mock_conn = MagicMock()
        cursor = mock_conn.cursor.return_value
        cursor.fetchone.return_value = (1,)  # user already exists
        with patch("database.db.Database.get_instance", return_value=mock_conn):
            resp = client.post("/signup", json={
                "username": "existing",
                "password": "secret123",
            })
        assert resp.status_code == 409
        assert "already taken" in resp.json()["detail"]

    def test_signup_missing_password_returns_422(self):
        resp = client.post("/signup", json={"username": "nopassword"})
        assert resp.status_code == 422

    def test_signup_missing_username_returns_422(self):
        resp = client.post("/signup", json={"password": "nousername"})
        assert resp.status_code == 422


class TestLoginEndpoint:
    def _mock_user_row(self, user_id=1, username="ahnaf", password="secret123"):
        hashed = hash_password(password)
        return (user_id, username, username, hashed)

    def test_login_success_returns_token(self):
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.fetchone.return_value = self._mock_user_row()
        with patch("database.db.Database.get_instance", return_value=mock_conn):
            resp = client.post("/login", json={
                "username": "ahnaf",
                "password": "secret123",
            })
        assert resp.status_code == 200
        assert "access_token" in resp.json()
        assert resp.json()["token_type"] == "bearer"

    def test_login_wrong_password_returns_401(self):
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.fetchone.return_value = self._mock_user_row()
        with patch("database.db.Database.get_instance", return_value=mock_conn):
            resp = client.post("/login", json={
                "username": "ahnaf",
                "password": "wrongpassword",
            })
        assert resp.status_code == 401

    def test_login_unknown_user_returns_401(self):
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.fetchone.return_value = None
        with patch("database.db.Database.get_instance", return_value=mock_conn):
            resp = client.post("/login", json={
                "username": "ghost",
                "password": "whatever",
            })
        assert resp.status_code == 401

    def test_login_account_without_password_returns_401(self):
        # CLI-created users have no password_hash
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.fetchone.return_value = (1, "test", "test", None)
        with patch("database.db.Database.get_instance", return_value=mock_conn):
            resp = client.post("/login", json={
                "username": "test",
                "password": "anything",
            })
        assert resp.status_code == 401


class TestFilesEndpointAuth:
    def _auth_header(self, user_id=5, username="test1"):
        token = create_token({"sub": str(user_id), "username": username})
        return {"Authorization": f"Bearer {token}"}

    def test_no_token_returns_401(self):
        resp = client.get("/files")
        assert resp.status_code == 403 or resp.status_code == 401

    def test_invalid_token_returns_401(self):
        resp = client.get("/files", headers={"Authorization": "Bearer garbage.token.here"})
        assert resp.status_code == 401

    def test_valid_token_returns_files(self):
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.fetchall.return_value = [
            (1, "SAM.txt", 52136, 1, "2026-06-30T10:37:58")
        ]
        with patch("database.db.Database.get_instance", return_value=mock_conn):
            resp = client.get("/files", headers=self._auth_header())
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "test1"
        assert data["user_id"] == 5
        assert len(data["files"]) == 1
        assert data["files"][0]["filename"] == "SAM.txt"

    def test_valid_token_with_no_files_returns_empty_list(self):
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.fetchall.return_value = []
        with patch("database.db.Database.get_instance", return_value=mock_conn):
            resp = client.get("/files", headers=self._auth_header())
        assert resp.status_code == 200
        assert resp.json()["files"] == []
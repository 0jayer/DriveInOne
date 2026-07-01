import jwt
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from api.main import app
from api.security import create_token, create_state_token, decode_state_token

client = TestClient(app)


def auth_header(user_id=5, username="test1"):
    token = create_token({"sub": str(user_id), "username": username})
    return {"Authorization": f"Bearer {token}"}


# --- State token unit tests ---

class TestStateToken:
    def test_create_and_decode_roundtrip(self):
        token = create_state_token(user_id=42)
        user_id = decode_state_token(token)
        assert user_id == 42

    def test_state_token_has_oauth_link_purpose(self):
        token = create_state_token(user_id=1)
        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["purpose"] == "oauth_link"

    def test_access_token_rejected_as_state_token(self):
        # A regular login token (purpose="access") should NOT work as a state token
        access_token = create_token({"sub": "1", "username": "test1"})
        with pytest.raises(jwt.InvalidTokenError):
            decode_state_token(access_token)

    def test_state_token_rejected_as_access_token(self):
        # get_current_user should reject a state token even though it's a valid JWT
        state_token = create_state_token(user_id=1)
        resp = client.get("/files", headers={"Authorization": f"Bearer {state_token}"})
        assert resp.status_code == 401

    def test_tampered_state_token_raises(self):
        token = create_state_token(user_id=1)
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(jwt.InvalidTokenError):
            decode_state_token(tampered)


# --- GET /accounts ---

class TestAccountsEndpoint:
    def test_requires_auth(self):
        resp = client.get("/accounts")
        assert resp.status_code in (401, 403)

    def test_returns_empty_list_when_no_providers(self):
        with patch("database.db.Database.get_instance", return_value=MagicMock()), \
             patch("api.main.load_providers", return_value=[]):
            resp = client.get("/accounts", headers=auth_header())
        assert resp.status_code == 200
        assert resp.json()["providers"] == []

    def test_returns_provider_details(self):
        fake_providers = [{
            "provider_id": 1,
            "name": "gdrive",
            "account_email": "user@gmail.com",
            "total_space": 16000000000,
            "used_space": 500000,
            "free_space": 15999500000,
            "instance": MagicMock(),
        }]
        with patch("database.db.Database.get_instance", return_value=MagicMock()), \
             patch("api.main.load_providers", return_value=fake_providers):
            resp = client.get("/accounts", headers=auth_header())
        assert resp.status_code == 200
        data = resp.json()["providers"]
        assert len(data) == 1
        assert data[0]["provider_type"] == "gdrive"
        assert data[0]["account_email"] == "user@gmail.com"
        assert data[0]["total_space_bytes"] == 16000000000
        assert data[0]["used_space_bytes"] == 500000

    def test_multiple_providers_all_returned(self):
        fake_providers = [
            {
                "provider_id": 1, "name": "gdrive", "account_email": "a@gmail.com",
                "total_space": 1000, "used_space": 100, "free_space": 900, "instance": MagicMock(),
            },
            {
                "provider_id": 2, "name": "dropbox", "account_email": "a@gmail.com",
                "total_space": 2000, "used_space": 200, "free_space": 1800, "instance": MagicMock(),
            },
        ]
        with patch("database.db.Database.get_instance", return_value=MagicMock()), \
             patch("api.main.load_providers", return_value=fake_providers):
            resp = client.get("/accounts", headers=auth_header())
        assert len(resp.json()["providers"]) == 2


# --- GET /accounts/gdrive/authorize ---

class TestGdriveAuthorize:
    def test_requires_auth(self):
        resp = client.get("/accounts/gdrive/authorize")
        assert resp.status_code in (401, 403)

    def test_returns_authorization_url(self):
        with patch("api.main.GoogleDriveProvider.get_authorization_url",
                   return_value="https://accounts.google.com/o/oauth2/auth?fake=1"):
            resp = client.get("/accounts/gdrive/authorize", headers=auth_header())
        assert resp.status_code == 200
        assert resp.json()["authorization_url"].startswith("https://accounts.google.com")

    def test_state_param_encodes_current_user(self):
        captured = {}

        def fake_get_url(credentials_path, redirect_uri, state):
            captured["state"] = state
            return "https://fake-url"

        with patch("api.main.GoogleDriveProvider.get_authorization_url", side_effect=fake_get_url):
            client.get("/accounts/gdrive/authorize", headers=auth_header(user_id=99))

        decoded_user_id = decode_state_token(captured["state"])
        assert decoded_user_id == 99


# --- GET /accounts/gdrive/callback ---

class TestGdriveCallback:
    def test_expired_or_invalid_state_redirects_to_login(self):
        resp = client.get(
            "/accounts/gdrive/callback",
            params={"code": "fakecode", "state": "not-a-real-token"},
            follow_redirects=False,
        )
        assert resp.status_code in (302, 307)
        assert "index.html?expired=1" in resp.headers["location"]

    def test_valid_flow_registers_provider_and_redirects_to_dashboard(self):
        state = create_state_token(user_id=7)
        mock_provider = MagicMock()
        mock_provider.get_account_email.return_value = "user@gmail.com"
        mock_provider.get_total_space.return_value = (1000, 100)

        # GoogleDriveProvider is replaced entirely with a MagicMock class stand-in.
        # exchange_code must be set on that SAME stand-in object, not the original
        # class, since patching the class name rebinds it to a new object.
        with patch("api.main.GoogleDriveProvider", return_value=mock_provider) as MockCls, \
             patch("api.main.register_provider") as mock_register, \
             patch("database.db.Database.get_instance", return_value=MagicMock()):
            MockCls.exchange_code = MagicMock(return_value=("access-tok", "refresh-tok"))
            resp = client.get(
                "/accounts/gdrive/callback",
                params={"code": "realcode", "state": state},
                follow_redirects=False,
            )

        assert resp.status_code in (302, 307)
        assert "dashboard.html?connected=gdrive" in resp.headers["location"]
        mock_register.assert_called_once()
        call_args = mock_register.call_args[0]
        assert call_args[1] == 7  # user_id from decoded state
        assert call_args[2] == "gdrive"


# --- GET /accounts/dropbox/authorize ---

class TestDropboxAuthorize:
    def test_requires_auth(self):
        resp = client.get("/accounts/dropbox/authorize")
        assert resp.status_code in (401, 403)

    def test_returns_authorization_url(self):
        with patch("api.main.DropboxProvider.get_authorization_url",
                   return_value="https://www.dropbox.com/oauth2/authorize?fake=1"):
            resp = client.get("/accounts/dropbox/authorize", headers=auth_header())
        assert resp.status_code == 200
        assert resp.json()["authorization_url"].startswith("https://www.dropbox.com")


# --- GET /accounts/dropbox/callback ---

class TestDropboxCallback:
    def test_expired_or_invalid_state_redirects_to_login(self):
        resp = client.get(
            "/accounts/dropbox/callback",
            params={"code": "fakecode", "state": "not-a-real-token"},
            follow_redirects=False,
        )
        assert resp.status_code in (302, 307)
        assert "index.html?expired=1" in resp.headers["location"]

    def test_valid_flow_registers_provider_and_redirects_to_dashboard(self):
        state = create_state_token(user_id=8)
        mock_provider = MagicMock()
        mock_provider.get_account_email.return_value = "user@dropbox.com"
        mock_provider.get_total_space.return_value = (2000, 200)

        with patch("api.main.DropboxProvider", return_value=mock_provider) as MockCls, \
             patch("api.main.register_provider") as mock_register, \
             patch("database.db.Database.get_instance", return_value=MagicMock()):
            MockCls.exchange_code = MagicMock(return_value=("access-tok", "refresh-tok"))
            resp = client.get(
                "/accounts/dropbox/callback",
                params={"code": "realcode", "state": state},
                follow_redirects=False,
            )

        assert resp.status_code in (302, 307)
        assert "dashboard.html?connected=dropbox" in resp.headers["location"]
        mock_register.assert_called_once()
        call_args = mock_register.call_args[0]
        assert call_args[1] == 8
        assert call_args[2] == "dropbox"
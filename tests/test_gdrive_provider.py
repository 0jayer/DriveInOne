import json
import pytest
from unittest.mock import MagicMock, patch, mock_open

from providers.gdrive import GoogleDriveProvider


FAKE_CREDS_FILE = json.dumps({
    "installed": {
        "client_id": "fake-client-id",
        "client_secret": "fake-client-secret"
    }
})


@pytest.fixture
def mock_build():
    """Patch googleapiclient.discovery.build so no real API client is created."""
    with patch("providers.gdrive.build") as mock_build_fn:
        mock_service = MagicMock()
        mock_build_fn.return_value = mock_service
        yield mock_build_fn, mock_service


@pytest.fixture
def provider_from_tokens(mock_build):
    """Build a GoogleDriveProvider using the token+refresh_token path (no browser OAuth)."""
    mock_build_fn, mock_service = mock_build

    with patch("builtins.open", mock_open(read_data=FAKE_CREDS_FILE)):
        with patch("providers.gdrive.Credentials") as MockCredentials:
            fake_creds = MagicMock()
            fake_creds.valid = True
            fake_creds.token = "fake-access-token"
            fake_creds.refresh_token = "fake-refresh-token"
            MockCredentials.return_value = fake_creds

            provider = GoogleDriveProvider(
                "fake_credentials.json",
                token="fake-access-token",
                refresh_token="fake-refresh-token"
            )

    return provider, mock_service


def test_loads_from_tokens_without_browser_oauth(provider_from_tokens):
    """Providing token+refresh_token should skip InstalledAppFlow entirely."""
    provider, mock_service = provider_from_tokens
    assert provider._service is mock_service


def test_refreshes_expired_token(mock_build):
    """If the reconstructed credentials are invalid/expired, .refresh() should be called."""
    mock_build_fn, mock_service = mock_build

    with patch("builtins.open", mock_open(read_data=FAKE_CREDS_FILE)):
        with patch("providers.gdrive.Credentials") as MockCredentials, \
             patch("providers.gdrive.Request"):
            fake_creds = MagicMock()
            fake_creds.valid = False  # force the refresh branch
            MockCredentials.return_value = fake_creds

            GoogleDriveProvider(
                "fake_credentials.json",
                token="expired-token",
                refresh_token="fake-refresh-token"
            )

            fake_creds.refresh.assert_called_once()


def test_get_tokens_returns_current_credentials(provider_from_tokens):
    provider, _ = provider_from_tokens
    provider._creds.token = "access-123"
    provider._creds.refresh_token = "refresh-456"

    token, refresh_token = provider.get_tokens()
    assert token == "access-123"
    assert refresh_token == "refresh-456"


def test_get_account_email(provider_from_tokens):
    provider, mock_service = provider_from_tokens
    mock_service.about().get().execute.return_value = {
        "user": {"emailAddress": "test@example.com"}
    }

    email = provider.get_account_email()
    assert email == "test@example.com"


def test_get_total_space(provider_from_tokens):
    provider, mock_service = provider_from_tokens
    mock_service.about().get().execute.return_value = {
        "storageQuota": {"limit": "1000000", "usage": "250000"}
    }

    total, used = provider.get_total_space()
    assert total == 1000000
    assert used == 250000


def test_get_free_space(provider_from_tokens):
    provider, mock_service = provider_from_tokens
    mock_service.about().get().execute.return_value = {
        "storageQuota": {"limit": "1000000", "usage": "250000"}
    }

    free = provider.get_free_space()
    assert free == 750000


def test_upload_bytes_calls_drive_create(provider_from_tokens):
    provider, mock_service = provider_from_tokens
    mock_service.files().create().execute.return_value = {
        "id": "fake-file-id", "name": "chunk_0"
    }

    result = provider.upload_bytes(b"hello world", "chunk_0")
    assert result["id"] == "fake-file-id"
    mock_service.files().create.assert_called()


def test_download_bytes_raises_if_not_found(provider_from_tokens):
    provider, mock_service = provider_from_tokens
    mock_service.files().list().execute.return_value = {"files": []}

    with pytest.raises(FileNotFoundError):
        provider.download_bytes("missing_chunk")


def test_delete_file_raises_if_not_found(provider_from_tokens):
    provider, mock_service = provider_from_tokens
    mock_service.files().list().execute.return_value = {"files": []}

    with pytest.raises(FileNotFoundError):
        provider.delete_file("missing_file")
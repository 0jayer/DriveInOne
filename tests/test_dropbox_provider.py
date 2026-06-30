import pytest
from unittest.mock import MagicMock, patch

from providers.dropbox import DropboxProvider


@pytest.fixture
def provider_from_tokens():
    """Build a DropboxProvider using the token+refresh_token path (no OAuth flow prompt)."""
    with patch("providers.dropbox.dropbox.Dropbox") as MockDropboxClient:
        mock_client = MagicMock()
        MockDropboxClient.return_value = mock_client

        provider = DropboxProvider(
            token="fake-access-token",
            refresh_token="fake-refresh-token"
        )

    return provider, mock_client


def test_loads_from_tokens_without_oauth_prompt(provider_from_tokens):
    provider, mock_client = provider_from_tokens
    assert provider._client is mock_client


def test_get_account_email(provider_from_tokens):
    provider, mock_client = provider_from_tokens
    fake_account = MagicMock()
    fake_account.email = "test@example.com"
    mock_client.users_get_current_account.return_value = fake_account

    email = provider.get_account_email()
    assert email == "test@example.com"


def test_get_total_space(provider_from_tokens):
    provider, mock_client = provider_from_tokens
    fake_usage = MagicMock()
    fake_usage.allocation.get_individual.return_value.allocated = 2147483648
    fake_usage.used = 500000
    mock_client.users_get_space_usage.return_value = fake_usage

    total, used = provider.get_total_space()
    assert total == 2147483648
    assert used == 500000


def test_get_free_space(provider_from_tokens):
    provider, mock_client = provider_from_tokens
    fake_usage = MagicMock()
    fake_usage.allocation.get_individual.return_value.allocated = 1000000
    fake_usage.used = 400000
    mock_client.users_get_space_usage.return_value = fake_usage

    free = provider.get_free_space()
    assert free == 600000


def test_upload_bytes_calls_files_upload(provider_from_tokens):
    provider, mock_client = provider_from_tokens
    provider.upload_bytes(b"hello world", "chunk_0")
    mock_client.files_upload.assert_called_once_with(b"hello world", "/chunk_0")


def test_download_bytes_returns_content(provider_from_tokens):
    provider, mock_client = provider_from_tokens
    fake_response = MagicMock()
    fake_response.content = b"chunk data here"
    mock_client.files_download.return_value = (MagicMock(), fake_response)

    data = provider.download_bytes("chunk_0")
    assert data == b"chunk data here"
    mock_client.files_download.assert_called_once_with("/chunk_0")


def test_delete_file_calls_files_delete_v2(provider_from_tokens):
    provider, mock_client = provider_from_tokens
    provider.delete_file("some_file")
    mock_client.files_delete_v2.assert_called_once_with("/some_file")


def test_list_files_returns_file_and_folder_entries(provider_from_tokens):
    provider, mock_client = provider_from_tokens

    file_entry = MagicMock()
    file_entry.name = "report.txt"
    file_entry.size = 1234
    file_entry.id = "id1"

    folder_entry = MagicMock(spec=["name", "id"])  # no `size` attribute → treated as folder
    folder_entry.name = "Documents"
    folder_entry.id = "id2"

    fake_result = MagicMock()
    fake_result.entries = [file_entry, folder_entry]
    mock_client.files_list_folder.return_value = fake_result

    files = provider.list_files()
    assert len(files) == 2
    assert files[0] == {"name": "report.txt", "size": 1234, "id": "id1"}
    assert files[1] == {"name": "Documents", "id": "id2"}
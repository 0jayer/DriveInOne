import pytest
from providers.base import StorageProvider


def test_abc_cannot_be_instantiated():
    with pytest.raises(TypeError):
        StorageProvider("bucket", "region")


def test_abc_rejects_partial_implementation():
    """Missing any abstract method should prevent instantiation."""
    class Incomplete(StorageProvider):
        def upload_file(self, file_path, remote_key): pass
        def upload_bytes(self, data, remote_key): pass
        def download_file(self, remote_key, local_path): pass
        # missing download_bytes and delete_file

    with pytest.raises(TypeError):
        Incomplete("bucket", "region")


def test_concrete_provider_instantiates():
    """A fully implemented provider should instantiate without error."""
    class Concrete(StorageProvider):
        def upload_file(self, file_path, remote_key): pass
        def upload_bytes(self, data, remote_key): pass
        def download_file(self, remote_key, local_path): pass
        def download_bytes(self, remote_key): return b""
        def delete_file(self, remote_key): pass

    p = Concrete("test-bucket", "us-east-1")
    assert p._bucket == "test-bucket"
    assert p._region == "us-east-1"
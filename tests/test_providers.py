import pytest
from distribution.upload import DistributionUpload
from providers.base import StorageProvider

def test_storage_provider_cannot_be_instantiated():
    with pytest.raises(TypeError):
        StorageProvider("my-bucket", "us-east-1")

def test_allocate_raises_when_not_enough_space():
    # create a DistributionUpload with file_size bigger than total provider space
    distribution_upload = DistributionUpload(file_size=1000, providers=[
        {"name": "provider1", "free_space": 400},
        {"name": "provider2", "free_space": 300},
    ])
    # assert it raises ValueError
    with pytest.raises(ValueError):
        distribution_upload.allocate()


def test_allocate_returns_correct_sizes():
    providers = [
        {"name": "provider1", "free_space": 500},
        {"name": "provider2", "free_space": 300},
        {"name": "provider3", "free_space": 200},
    ]
    file_size = 800
    distribution_upload = DistributionUpload(file_size=file_size, providers=providers)
    allocations = distribution_upload.allocate()
    total_allocated = sum(size for _, size, _ in allocations)
    assert total_allocated == file_size
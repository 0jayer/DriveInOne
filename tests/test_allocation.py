import os
import tempfile
import pytest
from distribution.upload import DistributionUpload


def make_temp_file(size_bytes: int) -> str:
    f = tempfile.NamedTemporaryFile(delete=False)
    f.write(b'\x00' * size_bytes)
    f.close()
    return f.name


def make_providers(*free_spaces):
    """Build a minimal provider dict list with given free_space values."""
    return [
        {"name": f"provider_{i}", "free_space": space, "provider_id": i + 1, "instance": None}
        for i, space in enumerate(free_spaces)
    ]


class TestAllocate:
    def test_single_provider_exact_fit(self):
        tmp = make_temp_file(100)
        try:
            dist = DistributionUpload(tmp, make_providers(100))
            allocations = dist.allocate()
            assert len(allocations) == 1
            _, size, offset, chunk_index = allocations[0]
            assert size == 100
            assert offset == 0
            assert chunk_index == 0
        finally:
            os.unlink(tmp)

    def test_single_provider_more_than_enough_space(self):
        tmp = make_temp_file(100)
        try:
            dist = DistributionUpload(tmp, make_providers(500))
            allocations = dist.allocate()
            assert len(allocations) == 1
            _, size, _, _ = allocations[0]
            assert size == 100
        finally:
            os.unlink(tmp)

    def test_split_across_two_providers(self):
        tmp = make_temp_file(300)
        try:
            dist = DistributionUpload(tmp, make_providers(200, 200))
            allocations = dist.allocate()
            assert len(allocations) == 2
            total = sum(size for _, size, _, _ in allocations)
            assert total == 300
        finally:
            os.unlink(tmp)

    def test_total_allocated_equals_file_size(self):
        tmp = make_temp_file(750)
        try:
            dist = DistributionUpload(tmp, make_providers(300, 300, 300))
            allocations = dist.allocate()
            total = sum(size for _, size, _, _ in allocations)
            assert total == 750
        finally:
            os.unlink(tmp)

    def test_offsets_are_contiguous_and_non_overlapping(self):
        tmp = make_temp_file(300)
        try:
            dist = DistributionUpload(tmp, make_providers(200, 200))
            allocations = dist.allocate()
            allocations_sorted = sorted(allocations, key=lambda a: a[3])  # by chunk_index
            cursor = 0
            for _, size, offset, _ in allocations_sorted:
                assert offset == cursor
                cursor += size
            assert cursor == 300
        finally:
            os.unlink(tmp)

    def test_greedy_fills_largest_provider_first(self):
        tmp = make_temp_file(300)
        try:
            providers = [
                {"name": "small", "free_space": 100, "provider_id": 1, "instance": None},
                {"name": "large", "free_space": 500, "provider_id": 2, "instance": None},
            ]
            dist = DistributionUpload(tmp, providers)
            allocations = dist.allocate()
            first_provider, _, _, _ = allocations[0]
            assert first_provider["name"] == "large"
        finally:
            os.unlink(tmp)

    def test_insufficient_space_raises_value_error(self):
        tmp = make_temp_file(500)
        try:
            dist = DistributionUpload(tmp, make_providers(100, 100))
            with pytest.raises(ValueError, match="Not enough free space"):
                dist.allocate()
        finally:
            os.unlink(tmp)

    def test_chunk_indices_are_sequential_from_zero(self):
        tmp = make_temp_file(300)
        try:
            dist = DistributionUpload(tmp, make_providers(200, 200))
            allocations = dist.allocate()
            indices = sorted(chunk_index for _, _, _, chunk_index in allocations)
            assert indices == list(range(len(allocations)))
        finally:
            os.unlink(tmp)

    def test_file_size_matches_actual_file(self):
        tmp = make_temp_file(250)
        try:
            dist = DistributionUpload(tmp, make_providers(500))
            assert dist.file_size == 250
        finally:
            os.unlink(tmp)
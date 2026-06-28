import threading

class DistributionUpload:
    def __init__(self, file_size, providers):
        self.file_size = file_size
        self.providers = providers

    def allocate(self):
        # 1. sort providers by free_space descending
        
        sorted_providers = sorted(self.providers, key=lambda p: p["free_space"], reverse=True)
        # 2. check total free space >= file_size, raise ValueError if not
        
        total_free_space = sum(p["free_space"] for p in sorted_providers)
        if total_free_space < self.file_size:
            raise ValueError("Not enough free space available")
        # 3. loop through sorted providers, calculate offset and size for each
        allocations = []
        remaining_size = self.file_size
        offset = 0
        for provider in sorted_providers:
            if remaining_size <= 0:
                break
            
            allocated_size = min(remaining_size, provider["free_space"])
            allocations.append((provider, allocated_size, offset))
            remaining_size -= allocated_size
            offset = self.file_size - remaining_size

        # 4. return a list of allocations
        return allocations
    
    def upload(self, allocations):
        threads = []
        for provider, size, offset in allocations:
            t = threading.Thread(target=self._upload_chunk, args=(provider, size, offset))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

    def _upload_chunk(self, provider, size, offset):
        print(f"Uploading {size} bytes to {provider['name']} at offset {offset}")
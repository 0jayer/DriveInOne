from providers.gdrive import GoogleDriveProvider
from providers.dropbox import DropboxProvider


class StorageFactory:
    _providers = {
        "gdrive": GoogleDriveProvider,
        "dropbox": DropboxProvider,
     }

    @staticmethod
    def get_provider(provider_name, **kwargs):
        if provider_name not in StorageFactory._providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        return StorageFactory._providers[provider_name](**kwargs)
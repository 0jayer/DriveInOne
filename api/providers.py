from database.providers import get_providers_for_user
from providers.gdrive import GoogleDriveProvider
from providers.dropbox import DropboxProvider
import os

GOOGLE_WEB_CREDENTIALS_PATH = (
    "/etc/secrets/google_credentials_web.json"
    if os.path.exists("/etc/secrets/google_credentials_web.json")
    else "credentials/google_credentials_web.json"
)


def load_providers(conn, user_id):
    """
    Load and instantiate all providers belonging to a user.
    Returns a list of provider dicts ready for DistributionUpload/Download.
    """
    rows = get_providers_for_user(conn, user_id)

    providers = []
    for provider_id, provider_type, account_email, token, refresh_token in rows:
        if provider_type == "gdrive":
            instance = GoogleDriveProvider(
                GOOGLE_WEB_CREDENTIALS_PATH,
                token=token,
                refresh_token=refresh_token
            )
        elif provider_type == "dropbox":
            instance = DropboxProvider(token=token, refresh_token=refresh_token)
        else:
            print(f"[Providers] Unknown provider type '{provider_type}' — skipping")
            continue

        free_space = instance.get_free_space()
        total_space, used_space = instance.get_total_space()

        providers.append({
            "name": provider_type,
            "account_email": account_email,
            "instance": instance,
            "free_space": free_space,
            "total_space": total_space,
            "used_space": used_space,
            "provider_id": provider_id,
        })

    return providers
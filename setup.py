from database.db import Database
from database.users import get_or_create_user
from database.providers import register_provider
from providers.gdrive import GoogleDriveProvider
from providers.dropbox import DropboxProvider


def setup_gdrive(conn, user_id):
    print("\n[Google Drive] Starting OAuth — browser will open...")
    provider = GoogleDriveProvider("credentials/google_credentials.json")
    email = provider.get_account_email()
    total, used = provider.get_total_space()
    access_token, refresh_token = provider.get_tokens()
    nickname = input(f"  Nickname for this Google account [{email}]: ").strip() or email
    register_provider(conn, user_id, "gdrive", email, nickname, total, used,
                      "https://drive.google.com", access_token, refresh_token)


def setup_dropbox(conn, user_id):
    print("\n[Dropbox] Starting OAuth flow...")
    provider = DropboxProvider()
    email = provider.get_account_email()
    total, used = provider.get_total_space()
    access_token, refresh_token = provider.get_tokens()
    nickname = input(f"  Nickname for this Dropbox account [{email}]: ").strip() or email
    register_provider(conn, user_id, "dropbox", email, nickname, total, used,
                      "https://dropbox.com", access_token, refresh_token)


def interactive_setup(conn, user_id):
    print("=== DriveInOne Setup ===")
    print("Which providers do you want to register?")
    print("  1) Google Drive")
    print("  2) Dropbox")
    print("  3) Both")

    choice = input("\nEnter choice (1/2/3): ").strip()

    if choice == "1":
        setup_gdrive(conn, user_id)
    elif choice == "2":
        setup_dropbox(conn, user_id)
    elif choice == "3":
        setup_gdrive(conn, user_id)
        setup_dropbox(conn, user_id)
    else:
        print("Invalid choice — exiting")
        return

    print("\n[Setup] Done.")


def main():
    conn = Database.get_instance()
    username = input("Username: ").strip()
    user_id = get_or_create_user(conn, username)
    interactive_setup(conn, user_id)


if __name__ == "__main__":
    main()
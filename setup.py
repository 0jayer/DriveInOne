import datetime
from database.db import Database
from providers.gdrive import GoogleDriveProvider
from providers.dropbox import DropboxProvider


def register_provider(conn, provider_type, email, nickname, total, used, url,
                      token=None, refresh_token=None):
    cursor = conn.cursor()

    cursor.execute(
        "SELECT provider_id FROM providers WHERE account_email = %s AND provider_type = %s",
        (email, provider_type)
    )
    existing = cursor.fetchone()

    if existing:
        print(f"[Setup] {provider_type} account '{email}' already registered (provider_id={existing[0]}) — skipping")
        return

    cursor.execute("""
        INSERT INTO providers (
            provider_type, account_email, account_nickname,
            total_space_bytes, used_space_bytes, website_url,
            token, refresh_token, last_synced
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING provider_id
    """, (
        provider_type, email, nickname,
        total, used, url,
        token, refresh_token,
        datetime.datetime.now(datetime.UTC).isoformat()
    ))

    provider_id = cursor.fetchone()[0]
    conn.commit()
    print(f"[Setup] Registered {provider_type} account '{email}' (provider_id={provider_id})")


def setup_gdrive(conn):
    print("\n[Google Drive] Starting OAuth — browser will open...")
    provider = GoogleDriveProvider("credentials/google_credentials.json")
    email = provider.get_account_email()
    total, used = provider.get_total_space()
    nickname = input(f"  Nickname for this account [{email}]: ").strip() or email
    register_provider(conn, "gdrive", email, nickname, total, used, "https://drive.google.com")


def setup_dropbox(conn):
    print("\n[Dropbox] Starting OAuth flow...")
    provider = DropboxProvider()  # triggers _run_oauth_flow
    email = provider.get_account_email()
    total, used = provider.get_total_space()
    access_token, refresh_token = provider.get_tokens()
    nickname = input(f"  Nickname for this account [{email}]: ").strip() or email
    register_provider(conn, "dropbox", email, nickname, total, used,
                      "https://dropbox.com", access_token, refresh_token)


def main():
    print("=== DriveInOne Setup ===")
    print("Which providers do you want to register?")
    print("  1) Google Drive")
    print("  2) Dropbox")
    print("  3) Both")

    choice = input("\nEnter choice (1/2/3): ").strip()

    conn = Database.get_instance()

    if choice == "1":
        setup_gdrive(conn)
    elif choice == "2":
        setup_dropbox(conn)
    elif choice == "3":
        setup_gdrive(conn)
        setup_dropbox(conn)
    else:
        print("Invalid choice — exiting")
        return

    print("\n[Setup] Done. Run 'python main.py' to start uploading.")


if __name__ == "__main__":
    main()
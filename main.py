import os
from database.db import Database
from providers.gdrive import GoogleDriveProvider
from providers.dropbox import DropboxProvider
from distribution.upload import DistributionUpload
from distribution.download import DistributionDownload


def load_providers(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT provider_id, provider_type, token, refresh_token
        FROM providers
        ORDER BY provider_id
    """)
    rows = cursor.fetchall()

    providers = []
    for provider_id, provider_type, token, refresh_token in rows:
        if provider_type == "gdrive":
            instance = GoogleDriveProvider("credentials/google_credentials.json")
        elif provider_type == "dropbox":
            instance = DropboxProvider(token=token, refresh_token=refresh_token)
        else:
            print(f"[Main] Unknown provider type '{provider_type}' — skipping")
            continue

        free_space = instance.get_free_space()
        #print(f"[Main] {provider_type} (id={provider_id}) — free: {free_space / 1e9:.2f} GB")

        total_space, used_space = instance.get_total_space()    # add this

        providers.append({
            "name": provider_type,
            "instance": instance,
            "free_space": free_space,
            "total_space": total_space,                         # add this
            "used_space": used_space,                           # add this
            "provider_id": provider_id,
        })

    return providers


def handle_upload(conn):
    file_path = input("Enter path to file to upload: ").strip()
    if not os.path.exists(file_path):
        print(f"[Main] File not found: {file_path}")
        return

    providers = load_providers(conn)
    if not providers:
        print("[Main] No providers registered. Run setup.py first.")
        return

    dist = DistributionUpload(file_path, providers)
    allocations = dist.allocate()

    print(f"\n[Main] Uploading '{os.path.basename(file_path)}' in {len(allocations)} chunk(s)...")
    dist.upload(allocations, owner="default")
    print("[Main] Upload complete.")


def handle_download():
    downloader = DistributionDownload()
    rows = downloader.list_files()
    if not rows:
        return

    file_id = input("\nEnter file_id to download: ").strip()
    if not file_id.isdigit():
        print("[Main] Invalid file_id.")
        return

    output_dir = input("Output directory (press Enter for current): ").strip() or "."
    downloader.download(int(file_id), output_dir=output_dir)

def display_storage_summary(providers):
    total_all = sum(p["total_space"] for p in providers)
    used_all  = sum(p["used_space"]  for p in providers)
    free_all  = sum(p["free_space"]  for p in providers)

    print("\n=== Storage Summary ===")
    print(f"  {'Provider':<12} {'Total':>10} {'Used':>10} {'Free':>10}")
    print("  " + "-" * 46)
    for p in providers:
        print(
            f"  {p['name']:<12}"
            f" {p['total_space']/1e9:>9.2f}G"
            f" {p['used_space']/1e9:>9.2f}G"
            f" {p['free_space']/1e9:>9.2f}G"
        )
    print("  " + "-" * 46)
    print(
        f"  {'TOTAL':<12}"
        f" {total_all/1e9:>9.2f}G"
        f" {used_all/1e9:>9.2f}G"
        f" {free_all/1e9:>9.2f}G"
    )
    print()

def main():
    conn = Database.get_instance()
    providers = load_providers(conn)

    if not providers:
        print("[Main] No providers registered. Run setup.py first.")
        return

    display_storage_summary(providers)    # add this
    print("=== DriveInOne ===")
    print("  1) Upload a file")
    print("  2) Download a file")
    print("  3) Exit")

    choice = input("\nChoice (1/2/3): ").strip()

    if choice == "1":
        handle_upload(conn)
    elif choice == "2":
        handle_download()
    elif choice == "3":
        return
    else:
        print("[Main] Invalid choice.")


if __name__ == "__main__":
    main()
<p align="center">
  <img src="assets/DriveInOne_logo.png" alt="DriveInOne Logo" width="700"/>
</p>

# DriveInOne
> **One app. All your cloud storage. One unified drive.**

DriveInOne is a virtual file system that connects all your cloud storage accounts — Google Drive, Dropbox, and more — and presents them as a single unified storage space. Files too large for one provider are automatically split across multiple providers and seamlessly reassembled on download.

---

## Features

- **Unified Storage View** — All your cloud accounts appear as one big drive
- **Multi-Provider Support** — Google Drive and Dropbox connected, more planned
- **Intelligent Distribution** — Greedy allocation fills providers by free space; splits large files across providers automatically
- **Chunk Reassembly** — Split files are downloaded and stitched back together transparently
- **SHA-256 Integrity Checks** — Every chunk and every file is verified on download
- **OAuth Authentication** — Short-lived tokens with automatic refresh per provider
- **Persistent Metadata** — PostgreSQL on Supabase tracks files, chunks, and provider info
- **Parallel Uploads** — All chunks upload simultaneously via threading
- **Storage Dashboard** — See total, used, and free space per provider at a glance

---

## Architecture

DriveInOne uses a provider-based architecture. Each cloud storage service implements a common interface defined in `providers/base.py`. A greedy allocation algorithm distributes file chunks across providers, and a PostgreSQL database tracks all metadata needed for reassembly.

```
DriveInOne/
│
├── providers/
│   ├── base.py           # Abstract base class — upload_file, upload_bytes,
│   │                     # download_file, download_bytes, delete_file
│   ├── factory.py        # Factory for instantiating the correct provider
│   ├── gdrive.py         # Google Drive provider (OAuth 2.0, Drive API v3)
│   ├── dropbox.py        # Dropbox provider (OAuth 2.0 with refresh tokens)
│   └── __init__.py
│
├── distribution/
│   ├── upload.py         # Greedy allocation + parallel chunk upload + DB recording
│   ├── download.py       # Chunk download + ordered reassembly + integrity checks
│   └── __init__.py
│
├── database/
│   ├── db.py             # PostgreSQL singleton connection (psycopg2)
│   ├── schema.sql        # Schema: providers, files, chunks tables
│   └── __init__.py
│
├── tests/
│   ├── test_providers.py   # ABC and interface tests
│   ├── test_allocation.py  # Greedy allocation logic tests
│   ├── test_upload.py      # Upload, remote key naming, checksum, DB write tests
│   └── test_download.py    # Reassembly, integrity verification, edge case tests
│
├── .github/workflows/
│   └── tests.yml         # CI: runs full test suite on every push
│
├── credentials/          # OAuth credential files (gitignored)
├── setup.py              # Interactive provider registration CLI
├── main.py               # Entry point: storage summary, upload, download
└── requirements.txt
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13+ |
| Database | PostgreSQL via Supabase |
| Google Drive | Google Drive API v3, OAuth 2.0 |
| Dropbox | Dropbox API v2, OAuth 2.0 with refresh tokens |
| Testing | pytest + pytest-mock (fully mocked, no credentials needed) |
| CI/CD | GitHub Actions |

---

## Getting Started

### Prerequisites

- Python 3.13+
- A Google account and/or Dropbox account
- A [Supabase](https://supabase.com) project (free tier is enough)

### Installation

```bash
git clone https://github.com/0jayer/DriveInOne.git
cd DriveInOne
python -m venv .venv
.venv\Scripts\activate        # Windows
# or
source .venv/bin/activate     # Linux/macOS
pip install -r requirements.txt
```

### Environment Setup

Create a `.env` file in the project root:

```env
DATABASE_URL=your_supabase_connection_string
DROPBOX_APP_KEY=your_dropbox_app_key
DROPBOX_APP_SECRET=your_dropbox_app_secret
```

### Database Setup

Run the schema against your Supabase project:

```bash
# paste the contents of database/schema.sql into the Supabase SQL editor
# or use psql:
psql $DATABASE_URL -f database/schema.sql
```

### Google Drive Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable the **Google Drive API**
3. Create **OAuth 2.0 credentials** (Desktop app) and download the JSON file
4. Place it at `credentials/google_credentials.json`

### Dropbox Setup

1. Go to the [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Create a new app with **Scoped Access**
3. Note your **App key** and **App secret** — add them to `.env`

### Register Your Providers

```bash
python setup.py
```

This opens the OAuth flow for each provider, fetches your account info automatically, and saves everything to the database. Run once per account you want to connect.

### Run

```bash
python main.py
```

```
=== Storage Summary ===
  Provider          Total       Used       Free
  ----------------------------------------------
  gdrive           16.11G      0.00G     16.11G
  dropbox           2.15G      0.00G      2.15G
  ----------------------------------------------
  TOTAL            18.26G      0.00G     18.26G

=== DriveInOne ===
  1) Upload a file
  2) Download a file
  3) Exit
```

---

## How File Distribution Works

When you upload a file, DriveInOne:

1. Queries each provider for its current free space
2. Sorts providers by free space (largest first)
3. Fills each provider greedily — if the file fits in one provider, it goes there whole; if not, it's split at the provider's boundary
4. Uploads all chunks in parallel
5. Records the file metadata and every chunk's location, size, and SHA-256 checksum in the database

On download, it queries the database for the chunk list, downloads each chunk from the correct provider, verifies every chunk's checksum, stitches them in order, and verifies the final file checksum before returning it.

---

## Running Tests

```bash
pytest tests/ -v
```

All tests are fully mocked — no real API credentials or database connection needed.

---

## Roadmap

- [x] Google Drive integration
- [x] Dropbox integration with OAuth refresh tokens
- [x] Greedy multi-provider file distribution
- [x] Chunk upload and reassembly
- [x] SHA-256 integrity verification
- [x] PostgreSQL metadata storage
- [x] Parallel uploads
- [x] Full test suite with CI/CD
- [ ] FastAPI web backend
- [ ] Web UI (file browser, upload/download, storage dashboard)
- [ ] OneDrive integration
- [ ] File search across all providers
- [ ] Multi-user support with accounts and sessions

---

## License

This project is licensed under the Apache 2.0 License — see the [LICENSE](LICENSE) file for details.

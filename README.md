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
- **Multi-User Accounts** — Signup/login with hashed passwords and JWT-based sessions; each user manages their own set of connected providers
- **Web-Based OAuth Linking** — Connect Google Drive or Dropbox straight from the browser, no CLI needed
- **Intelligent Distribution** — Greedy allocation fills providers by free space; splits large files across providers automatically
- **Chunk Reassembly** — Split files are downloaded and stitched back together transparently
- **SHA-256 Integrity Checks** — Every chunk and every file is verified on download
- **OAuth Authentication** — Short-lived tokens with automatic refresh per provider
- **Persistent Metadata** — PostgreSQL on Supabase tracks users, files, chunks, and provider info
- **Parallel Uploads** — All chunks upload simultaneously via threading
- **Storage Dashboard** — See live total, used, and free space per provider at a glance, in-browser
- **REST API** — FastAPI backend with interactive docs at `/docs`

---

## Architecture

DriveInOne uses a provider-based architecture. Each cloud storage service implements a common interface defined in `providers/base.py`. A greedy allocation algorithm distributes file chunks across providers, and a PostgreSQL database tracks all metadata needed for reassembly. A FastAPI layer exposes everything over HTTP, backed by a plain HTML/CSS/JS frontend.

```
DriveInOne/
│
├── api/
│   ├── main.py            # FastAPI app — auth, upload, accounts, OAuth callbacks
│   ├── security.py        # Password hashing (bcrypt) + JWT creation/validation
│   ├── providers.py       # Shared provider-loading logic (CLI + API)
│   └── __init__.py
│
├── frontend/
│   ├── index.html         # Login / signup page
│   ├── dashboard.html     # Main app — provider cards, upload, file list
│   ├── app.js              # API client, auth/session helpers, toasts
│   └── style.css           # Design tokens and component styles
│
├── providers/
│   ├── base.py            # Abstract base class — upload_file, upload_bytes,
│   │                       # download_file, download_bytes, delete_file
│   ├── factory.py         # Factory for instantiating the correct provider
│   ├── gdrive.py           # Google Drive provider (OAuth 2.0, Drive API v3,
│   │                       # both Desktop-flow and web-redirect-flow support)
│   ├── dropbox.py          # Dropbox provider (OAuth 2.0 with refresh tokens,
│   │                       # both CLI-flow and web-redirect-flow support)
│   └── __init__.py
│
├── distribution/
│   ├── upload.py           # Greedy allocation + parallel chunk upload + DB recording
│   ├── download.py         # Chunk download + ordered reassembly + integrity checks
│   └── __init__.py
│
├── database/
│   ├── db.py               # PostgreSQL singleton connection (psycopg2)
│   ├── schema.sql          # Schema: users, providers, files, chunks tables
│   ├── users.py            # User creation/lookup (CLI + API paths)
│   ├── providers.py        # Provider registration/lookup queries
│   ├── files.py            # File and chunk metadata queries
│   └── __init__.py
│
├── tests/
│   ├── test_provider.py            # ABC and interface tests
│   ├── test_allocation.py          # Greedy allocation logic tests
│   ├── test_upload.py              # Upload, remote key naming, checksum, DB write tests
│   ├── test_download.py            # Reassembly, integrity verification, edge case tests
│   ├── test_gdrive_provider.py     # Mocked Google Drive provider tests
│   ├── test_dropbox_provider.py    # Mocked Dropbox provider tests
│   ├── test_auth.py                # Password hashing, JWT, signup/login/files endpoint tests
│   ├── test_upload_endpoint.py     # POST /upload endpoint tests
│   └── test_oauth_and_accounts.py  # State tokens, /accounts, OAuth authorize+callback tests
│
├── .github/workflows/
│   └── tests.yml           # CI: runs full test suite on every push
│
├── credentials/            # OAuth credential files (gitignored)
├── setup.py                # Interactive provider registration CLI (local/dev use)
├── main.py                 # CLI entry point: storage summary, upload, download
└── requirements.txt
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13+ |
| Backend | FastAPI + Uvicorn |
| Auth | bcrypt password hashing, JWT (PyJWT, HS256) |
| Frontend | Plain HTML/CSS/JS — no framework, no build step |
| Database | PostgreSQL (Supabase) |
| Google Drive | Google Drive API v3, OAuth 2.0 (Desktop + Web client flows) |
| Dropbox | Dropbox API v2, OAuth 2.0 with refresh tokens |
| Testing | pytest + pytest-mock (fully mocked, no live credentials or DB needed) |
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
SECRET_KEY=a_long_random_string_for_signing_jwts
```

### Database Setup

Run the schema against your Supabase project:

```bash
# paste the contents of database/schema.sql into the Supabase SQL editor
# or use psql:
psql $DATABASE_URL -f database/schema.sql
```

### Google Drive Setup

DriveInOne uses **two** Google OAuth clients:

1. **Desktop client** — for the local CLI flow (`setup.py`)
   - Go to the [Google Cloud Console](https://console.cloud.google.com/), enable the **Google Drive API**
   - Create OAuth 2.0 credentials of type **Desktop app**, download the JSON
   - Place it at `credentials/google_credentials.json`

2. **Web client** — for the browser-based "Connect Google Drive" flow
   - Create a second OAuth 2.0 credential of type **Web application** in the same project
   - Add `http://127.0.0.1:8000/accounts/gdrive/callback` as an authorized redirect URI
   - Download the JSON and place it at `credentials/google_credentials_web.json`

Both files are gitignored — they contain real secrets.

### Dropbox Setup

1. Go to the [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Create a new app with **Scoped Access**
3. Note your **App key** and **App secret** — add them to `.env`
4. Add `http://127.0.0.1:8000/accounts/dropbox/callback` to the app's redirect URI allowlist (needed for the web-based connect flow)

### Running the app

**Backend:**
```bash
uvicorn api.main:app --reload
```
API docs available at `http://127.0.0.1:8000/docs`.

**Frontend:**
```bash
cd frontend
python -m http.server 5500
```
Open `http://127.0.0.1:5500` in a browser — sign up, log in, connect a provider, and upload a file.

**CLI (alternative, local-only):**
```bash
python setup.py    # register provider accounts via OAuth
python main.py     # storage summary, upload, download
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
  3) Add another account
  4) Exit
```

---

## API Overview

| Method | Path | Auth | Description |
|--------|------|------|--------------|
| GET | `/` | — | Health check |
| POST | `/signup` | — | Create a new account |
| POST | `/login` | — | Verify credentials, returns a JWT access token |
| GET | `/files` | Bearer | List the authenticated user's files |
| POST | `/upload` | Bearer | Upload a file, distributed across the user's providers |
| GET | `/accounts` | Bearer | List connected providers with live capacity |
| GET | `/accounts/gdrive/authorize` | Bearer | Get the Google consent URL |
| GET | `/accounts/gdrive/callback` | — | Google OAuth redirect target — links the account |
| GET | `/accounts/dropbox/authorize` | Bearer | Get the Dropbox consent URL |
| GET | `/accounts/dropbox/callback` | — | Dropbox OAuth redirect target — links the account |

Full interactive documentation, including request/response schemas, is available at `/docs` once the server is running.

---

## How File Distribution Works

When you upload a file, DriveInOne:

1. Queries each of your connected providers for its current free space
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

All tests are fully mocked — no real API credentials or live database connection needed.

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
- [x] Multi-user support with accounts and JWT sessions
- [x] FastAPI web backend
- [x] Web-based OAuth linking for Google Drive and Dropbox
- [x] Web UI — login/signup, storage dashboard, drag-and-drop upload, file list
- [ ] File download from the web UI (API endpoint in progress)
- [ ] Disconnect/unlink a provider from the web UI
- [ ] OneDrive integration
- [ ] File search across all providers
- [ ] AI-assisted storage management (exploratory)

---

## License

This project is licensed under the Apache 2.0 License — see the [LICENSE](LICENSE) file for details.
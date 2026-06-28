# DriveInOne 

> **One app. All your cloud storage. One unified drive.**

DriveInOne is a virtual file system that connects all your cloud storage accounts — Google Drive, Dropbox, OneDrive, and more — and presents them as a single unified storage space. Upload, download, delete, and browse all your files, images, and videos from one place.

---

## Features

- **Unified Storage View** — All your cloud accounts appear as one big drive
- **Multi-Provider Support** — Google Drive, Dropbox (and more planned)
- **File Operations** — Upload, download, delete, and list files across any provider
- **Media Support** — Works with documents, images, videos, and any file type
- **Provider Abstraction** — Clean base class architecture makes adding new providers straightforward
- **OAuth Authentication** — Secure, token-based login per provider
- **Persistent Metadata** — SQLite database tracks files and provider information locally

---

## Architecture

DriveInOne uses a provider-based architecture. Each cloud storage service implements a common base interface defined in `providers/base.py`. A factory pattern handles provider instantiation, and a local database layer tracks file metadata across all connected accounts.

```
DriveInOne/
│
├── providers/
│   ├── base.py          # Abstract base class — common interface for all providers
│   ├── factory.py       # Factory for instantiating the correct provider
│   ├── gdrive.py        # Google Drive provider
│   ├── dropbox.py       # Dropbox provider
│   └── __init__.py
│
├── distribution/
│   ├── upload.py        # Upload distribution logic across providers
│   └── __init__.py
│
├── database/
│   ├── db.py            # Database access layer
│   ├── schema.sql       # SQLite schema definition
│   └── __init__.py
│
├── credentials/         # OAuth credential files (not tracked in git)
├── main.py
└── requirements.txt
```

---

##  Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Database | SQLite *(PostgreSQL migration planned)* |
| Auth | Google OAuth 2.0 |
| Google Drive | Google Drive API v3 |
| Dropbox | Dropbox API v2 |

---

##  Getting Started

### Prerequisites

- Python 3.13
- A Google account and/or Dropbox account
- Cloud provider API credentials (see setup below)

### Installation

```bash
git clone https://github.com/0jayer/DriveInOne.git
cd DriveInOne
python -m venv .venv
.venv\Scripts\activate   # Windows
# or
source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

### Google Drive Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable the **Google Drive API**
3. Create OAuth 2.0 credentials and download the JSON file
4. Place it at `credentials/google_credentials.json`

### Dropbox Setup

1. Go to the [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Create a new app and generate an access token
3. Place your credentials at `credentials/dropbox_credentials.json`

---

## 🗺️ Roadmap

- [x] Google Drive integration
- [ ] Dropbox integration
- [ ] OneDrive integration
- [ ] PostgreSQL migration
- [ ] Unified file browser CLI
- [ ] Web UI
- [ ] File search across all providers
- [ ] Storage usage dashboard

---

## 📄 License

This project is licensed under the Apache 2.0 License — see the [LICENSE](LICENSE) file for details.

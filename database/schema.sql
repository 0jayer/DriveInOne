CREATE TABLE IF NOT EXISTS users (
    user_id       SERIAL PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    display_name  TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS providers (
    provider_id       SERIAL PRIMARY KEY,
    user_id           INTEGER NOT NULL,
    provider_type     TEXT NOT NULL,
    account_email     TEXT NOT NULL,
    account_nickname  TEXT,
    token             TEXT,
    refresh_token     TEXT,
    token_expiry      TEXT,
    total_space_bytes BIGINT NOT NULL,
    used_space_bytes  BIGINT NOT NULL,
    website_url       TEXT,
    last_synced       TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS files (
    file_id                             SERIAL PRIMARY KEY,
    user_id                             INTEGER NOT NULL,
    original_filename                   TEXT NOT NULL,
    file_type                           TEXT NOT NULL,
    total_size_bytes                    BIGINT NOT NULL,
    total_chunks                        INTEGER,
    virtual_path                        TEXT NOT NULL,
    uploaded_at                         TEXT NOT NULL,
    checksum_file                       TEXT,
    uploaded_provider_id                INTEGER NOT NULL,
    FOREIGN KEY (user_id)               REFERENCES users(user_id),
    FOREIGN KEY (uploaded_provider_id)  REFERENCES providers(provider_id)
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id                    SERIAL PRIMARY KEY,
    file_id                     INTEGER NOT NULL,
    chunk_index                 INTEGER NOT NULL,
    chunk_size_bytes            BIGINT NOT NULL,
    remote_key                  TEXT NOT NULL,
    checksum_chunk              TEXT NOT NULL,
    provider_id                 INTEGER           NOT NULL,
    FOREIGN KEY (provider_id)   REFERENCES providers(provider_id),
    FOREIGN KEY (file_id)       REFERENCES files(file_id)
);
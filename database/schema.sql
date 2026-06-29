CREATE TABLE IF NOT EXISTS providers (
    provider_id       SERIAL PRIMARY KEY ,
    provider_type     TEXT NOT NULL,
    account_email     TEXT NOT NULL,
    account_nickname  TEXT,
    token             TEXT,
    refresh_token     TEXT,
    token_expiry      TEXT,
    total_space_bytes BIGINT,
    used_space_bytes  BIGINT,
    website_url       TEXT,
    last_synced       TEXT
);


CREATE TABLE IF NOT EXISTS files (
    file_id                             SERIAL PRIMARY KEY ,
    original_filename                   TEXT NOT NULL,
    file_type                           TEXT NOT NULL,
    total_size_bytes                    INTEGER NOT NULL,
    total_chunks                        INTEGER,
    virtual_path                        TEXT NOT NULL,
    uploaded_at                         TEXT NOT NULL,
    checksum_file                       TEXT,
    owner                               TEXT NOT NULL,
    uploaded_provider_id                INTEGER NOT NULL,
    FOREIGN KEY (uploaded_provider_id)  REFERENCES providers(provider_id)
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id                    SERIAL PRIMARY KEY,
    file_id                     INTEGER NOT NULL,
    chunk_index                 INTEGER NOT NULL,
    chunk_size_bytes            INTEGER NOT NULL,
    remote_key                  TEXT NOT NULL,
    checksum_chunk              TEXT NOT NULL,
    provider_id INTEGER         NOT NULL,
    FOREIGN KEY (provider_id)   REFERENCES providers(provider_id),
    FOREIGN KEY (file_id)       REFERENCES files(file_id)
);
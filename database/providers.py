import datetime


def register_provider(conn, user_id, provider_type, email, nickname, total, used, url,
                      token=None, refresh_token=None):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT provider_id FROM providers WHERE account_email = %s AND provider_type = %s AND user_id = %s",
        (email, provider_type, user_id)
    )
    existing = cursor.fetchone()
    if existing:
        print(f"[DB] {provider_type} account '{email}' already registered for this user (provider_id={existing[0]}) — skipping")
        return existing[0]

    cursor.execute("""
        INSERT INTO providers (
            user_id, provider_type, account_email, account_nickname,
            total_space_bytes, used_space_bytes, website_url,
            token, refresh_token, last_synced
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING provider_id
    """, (
        user_id, provider_type, email, nickname,
        total, used, url,
        token, refresh_token,
        datetime.datetime.now(datetime.UTC).isoformat()
    ))
    provider_id = cursor.fetchone()[0]
    conn.commit()
    print(f"[DB] Registered {provider_type} account '{email}' (provider_id={provider_id})")
    return provider_id

def get_provider_by_id(conn, provider_id):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT provider_type, token, refresh_token FROM providers WHERE provider_id = %s",
        (provider_id,)
    )
    return cursor.fetchone()

def get_providers_for_user(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT provider_id, provider_type, token, refresh_token
        FROM providers
        WHERE user_id = %s
        ORDER BY provider_id
    """, (user_id,))
    return cursor.fetchall()
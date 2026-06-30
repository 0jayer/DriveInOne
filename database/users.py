# import datetime

# def get_or_create_user(conn, username):
#     cursor = conn.cursor()
#     cursor.execute("SELECT user_id, display_name FROM users WHERE username = %s", (username,))
#     row = cursor.fetchone()

#     if row:
#         user_id, display_name = row
#         print(f"[Users] Welcome back, {display_name or username} (user_id={user_id})")
#         return user_id

#     display_name = input(f"  No account found for '{username}'. Display name to use: ").strip() or username
#     cursor.execute("""
#         INSERT INTO users (username, display_name, created_at)
#         VALUES (%s, %s, %s)
#         RETURNING user_id
#     """, (username, display_name, datetime.datetime.now(datetime.UTC).isoformat()))
#     user_id = cursor.fetchone()[0]
#     conn.commit()
#     print(f"[Users] Created new user '{username}' (user_id={user_id})")
#     return user_id

import datetime


def create_user(conn, username, hashed_password, display_name=None):
    """
    Used by the API signup endpoint. Hashing is done by the caller (api/security.py),
    this function only stores the already-hashed password.
    Raises ValueError if username is already taken.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
    if cursor.fetchone():
        raise ValueError(f"Username '{username}' is already taken")

    display_name = display_name or username
    cursor.execute("""
        INSERT INTO users (username, display_name, password_hash, created_at)
        VALUES (%s, %s, %s, %s)
        RETURNING user_id
    """, (username, display_name, hashed_password, datetime.datetime.now(datetime.UTC).isoformat()))
    user_id = cursor.fetchone()[0]
    conn.commit()
    print(f"[Users] Created new user '{username}' (user_id={user_id})")
    return user_id


def get_user_by_username(conn, username):
    """
    Returns (user_id, username, display_name, password_hash) or None.
    Used by the login endpoint to verify credentials.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, username, display_name, password_hash FROM users WHERE username = %s",
        (username,)
    )
    return cursor.fetchone()


def get_or_create_user(conn, username, display_name=None):
    """
    CLI-only function used by main.py and setup.py.
    Not used by the API — the API uses create_user + get_user_by_username.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, display_name FROM users WHERE username = %s", (username,))
    row = cursor.fetchone()

    if row:
        user_id, existing_display_name = row
        print(f"[Users] Welcome back, {existing_display_name or username} (user_id={user_id})")
        return user_id

    if display_name is None:
        display_name = input(f"  No account found for '{username}'. Display name to use: ").strip() or username

    cursor.execute("""
        INSERT INTO users (username, display_name, created_at)
        VALUES (%s, %s, %s)
        RETURNING user_id
    """, (username, display_name, datetime.datetime.now(datetime.UTC).isoformat()))
    user_id = cursor.fetchone()[0]
    conn.commit()
    print(f"[Users] Created new user '{username}' (user_id={user_id})")
    return user_id
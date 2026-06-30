import datetime

def get_or_create_user(conn, username):
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, display_name FROM users WHERE username = %s", (username,))
    row = cursor.fetchone()

    if row:
        user_id, display_name = row
        print(f"[Users] Welcome back, {display_name or username} (user_id={user_id})")
        return user_id

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
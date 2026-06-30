def insert_file(conn, user_id, filename, file_ext, total_size, total_chunks,
                 virtual_path, uploaded_at, checksum, primary_provider_id):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO files (
            user_id, original_filename, file_type, total_size_bytes, total_chunks,
            virtual_path, uploaded_at, checksum_file, uploaded_provider_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING file_id
    """, (
        user_id, filename, file_ext, total_size, total_chunks,
        virtual_path, uploaded_at, checksum, primary_provider_id
    ))
    file_id = cursor.fetchone()[0]
    conn.commit()
    return file_id


def insert_chunk(conn, file_id, chunk_index, chunk_size, remote_key, checksum, provider_id):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chunks (
            file_id, chunk_index, chunk_size_bytes,
            remote_key, checksum_chunk, provider_id
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """, (file_id, chunk_index, chunk_size, remote_key, checksum, provider_id))


def get_files_for_user(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT file_id, original_filename, total_size_bytes, total_chunks, uploaded_at
        FROM files
        WHERE user_id = %s
        ORDER BY uploaded_at DESC
    """, (user_id,))
    return cursor.fetchall()


def get_file_metadata(conn, file_id):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT original_filename, total_size_bytes, total_chunks, checksum_file
        FROM files WHERE file_id = %s
    """, (file_id,))
    return cursor.fetchone()


def get_chunks_for_file(conn, file_id):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT chunk_index, provider_id, remote_key, chunk_size_bytes, checksum_chunk
        FROM chunks
        WHERE file_id = %s
        ORDER BY chunk_index ASC
    """, (file_id,))
    return cursor.fetchall()
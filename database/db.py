import os

import numpy as np
import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

load_dotenv()


def get_conn() -> psycopg.Connection:
    conn = psycopg.connect(os.environ["DATABASE_URL"], autocommit=True, connect_timeout=5)
    register_vector(conn)
    return conn


def insert_email(conn, user_id: str, email: dict, ciphertext: bytes, nonce: bytes, key_id: str):
    """Insert one email row. Returns the new email id, or None if it already existed."""
    row = conn.execute(
        """
        INSERT INTO emails
            (user_id, provider_id, thread_id, sent_at, labels, ciphertext, nonce, key_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id, provider_id) DO NOTHING
        RETURNING id
        """,
        (
            user_id,
            email["provider_id"],
            email.get("thread_id"),
            email["sent_at"],
            email.get("labels", []),
            ciphertext,
            nonce,
            key_id,
        ),
    ).fetchone()
    return row[0] if row else None


def insert_chunks(conn, email_id, user_id: str, chunks: list, model_name: str):
    """chunks is a list of (chunk_idx, vector). Saves one row per chunk."""
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO email_chunks (email_id, user_id, chunk_idx, embedding, embed_model)
            VALUES (%s, %s, %s, %s, %s)
            """,
            [(email_id, user_id, idx, np.array(vec), model_name) for idx, vec in chunks],
        )


def search_chunks(conn, user_id: str, qvec: list, k: int, after=None, before=None):
    """Find the k closest chunks for this user, optionally limited to a date range."""
    return conn.execute(
        """
        SELECT c.email_id, c.chunk_idx, c.embedding <=> %s AS dist
        FROM email_chunks c
        JOIN emails e ON e.id = c.email_id
        WHERE c.user_id = %s
          AND (%s::timestamptz IS NULL OR e.sent_at >= %s::timestamptz)
          AND (%s::timestamptz IS NULL OR e.sent_at <  %s::timestamptz)
        ORDER BY dist
        LIMIT %s
        """,
        (np.array(qvec), user_id, after, after, before, before, k),
    ).fetchall()

def list_emails(conn, user_id: str, after=None, before=None, limit: int = 10):
    """Newest first, no vector search. Returns a list of email ids."""
    rows = conn.execute(
        """
        SELECT id FROM emails
        WHERE user_id = %s
          AND (%s::timestamptz IS NULL OR sent_at >= %s::timestamptz)
          AND (%s::timestamptz IS NULL OR sent_at <  %s::timestamptz)
        ORDER BY sent_at DESC
        LIMIT %s
        """,
        (user_id, after, after, before, before, limit),
    ).fetchall()
    return [r[0] for r in rows]

def fetch_emails(conn, user_id: str, email_ids: list):
    """Load email rows (still encrypted) for this user."""
    rows = conn.execute(
        """
        SELECT id, provider_id, thread_id, sent_at, labels, ciphertext, nonce
        FROM emails
        WHERE user_id = %s AND id = ANY(%s::uuid[])
        """,
        (user_id, email_ids),
    ).fetchall()
    return [
        {
            "id": r[0],
            "provider_id": r[1],
            "thread_id": r[2],
            "sent_at": r[3],
            "labels": r[4],
            "ciphertext": bytes(r[5]),
            "nonce": bytes(r[6]),
        }
        for r in rows
    ]
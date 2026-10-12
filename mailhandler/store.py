import uuid

from mailhandler.crypto import encrypt_email, decrypt_email
from database.db import insert_email, insert_chunks, search_chunks, fetch_emails, list_emails
from mailhandler.embed import embed, EMBED_MODEL


def _norm(user_id) -> str:
    """Always use the same string form of a user id (it's part of the encryption AAD)."""
    return str(uuid.UUID(str(user_id)))


def chunk_text(text: str) -> list[str]:
    """For now every email is one chunk. Split long emails here later."""
    return [text]


def build_embed_text(email: dict) -> str:
    """Text that gets embedded: metadata first, then the body."""
    return (
        f"From: {email['sender']}\n"
        f"Subject: {email['subject']}\n"
        f"Date: {email['sent_at']}\n\n"
        f"{email['body']}"
    )


def save_email(conn, user_id, email: dict) -> bool:
    """Embed + encrypt one email and store it. Returns False if it was already saved."""
    user_id = _norm(user_id)

    # 1. Embed BEFORE opening the transaction (the model is the slow part)
    pieces = chunk_text(build_embed_text(email))
    chunks = [(i, embed(piece)) for i, piece in enumerate(pieces)]

    # 2. Encrypt the sensitive fields as one blob
    payload = {
        "v": 1,
        "subject": email["subject"],
        "sender": email["sender"],
        "to": email.get("to", []),
        "body": email["body"],
    }
    ciphertext, nonce, key_id = encrypt_email(payload, user_id, email["provider_id"])

    # 3. Save the email row and its chunks together, all or nothing
    with conn.transaction():
        email_id = insert_email(conn, user_id, email, ciphertext, nonce, key_id)
        if email_id is None:
            return False
        insert_chunks(conn, email_id, user_id, chunks, EMBED_MODEL)
    return True


def search(conn, user_id, query: str = "", limit: int = 5,
           after=None, before=None, newest_first: bool = False) -> list[dict]:
    """Find emails. With a query: vector search. With newest_first: re-sort the matches by date."""
    user_id = _norm(user_id)

    if query and query.strip():
        # when we sort by date afterwards, look at more candidates so the newest one isn't missed
        pool = max(limit * 10, 40) if newest_first else limit * 3
        hits = search_chunks(conn, user_id, embed(query), pool, after, before)

        best = {}
        for email_id, _chunk_idx, dist in hits:
            if email_id not in best or dist < best[email_id]:
                best[email_id] = dist
        ranked = sorted(best.items(), key=lambda item: item[1])
        if not newest_first:
            ranked = ranked[:limit]
        else:
            ranked = ranked[:max(limit * 4, 20)]       # keep the most relevant ones, sort by date below
    else:
        ids = list_emails(conn, user_id, after, before, limit)   # already newest first
        ranked = [(i, 0.0) for i in ids]

    if not ranked:
        return []

    rows = fetch_emails(conn, user_id, [email_id for email_id, _ in ranked])
    by_id = {row["id"]: row for row in rows}
    ranked = [(i, d) for i, d in ranked if i in by_id]

    if newest_first or not (query and query.strip()):
        ranked.sort(key=lambda item: by_id[item[0]]["sent_at"], reverse=True)
    ranked = ranked[:limit]

    results = []
    for email_id, dist in ranked:
        row = by_id[email_id]
        data = decrypt_email(row["ciphertext"], row["nonce"], user_id, row["provider_id"])
        results.append({
            "id": str(email_id),
            "distance": round(dist, 3),
            "sent_at": row["sent_at"].isoformat(),
            "sender": data["sender"],
            "subject": data["subject"],
            "snippet": data["body"][:500],
        })
    return results
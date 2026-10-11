import base64
import os
import re
from datetime import datetime, timezone
from email.utils import getaddresses

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from googleapiclient.errors import HttpError

from Helpers.get_gmail_service import get_gmail_read_service          # wherever your auth code lives
from database.db import get_conn
from mailhandler.store import save_email
import time

load_dotenv()


# ---------- parsing ----------

def _header(headers: list, name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _decode(data: str) -> str:
    """Gmail sends body data as base64url."""
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")


def _walk(part: dict, plain: list, html: list):
    """Emails are trees of parts (multipart/alternative, attachments...). Collect the text ones."""
    mime = part.get("mimeType", "")
    data = part.get("body", {}).get("data")
    if data and not part.get("filename"):          # skip attachments
        if mime == "text/plain":
            plain.append(_decode(data))
        elif mime == "text/html":
            html.append(_decode(data))
    for sub in part.get("parts", []):
        _walk(sub, plain, html)


def clean_body(text: str) -> str:
    """Drop quoted replies and signatures. This is a starting point, tune it on your own mail."""
    kept = []
    for line in text.splitlines():
        stripped = line.strip()
        if line.startswith(">"):
            continue
        if re.match(r"^On .+ wrote:$", stripped) or stripped == "--":
            break
        kept.append(line.rstrip())
    text = "\n".join(kept)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract_body(payload: dict) -> str:
    plain, html = [], []
    _walk(payload, plain, html)
    if plain:                                       # prefer text/plain
        text = "\n".join(plain)
    elif html:
        soup = BeautifulSoup("\n".join(html), "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text("\n")
    else:
        text = ""
    return clean_body(text)[:20000]                 # cap absurdly long bodies


def parse_message(msg: dict) -> dict:
    payload = msg["payload"]
    headers = payload.get("headers", [])
    sent_at = datetime.fromtimestamp(int(msg["internalDate"]) / 1000, tz=timezone.utc).isoformat()
    to_addrs = [addr for _, addr in getaddresses([_header(headers, "To")]) if addr]
    return {
        "provider_id": msg["id"],                   # Gmail's own message id
        "thread_id": msg["threadId"],
        "sent_at": sent_at,
        "sender": _header(headers, "From"),
        "to": to_addrs,
        "subject": _header(headers, "Subject") or "(no subject)",
        "body": extract_body(payload),
        "labels": msg.get("labelIds", []),
    }


# ---------- fetching ----------

def list_message_ids(service, query: str, max_messages: int | None = None) -> list[str]:
    ids, token = [], None
    while max_messages is None or len(ids) < max_messages:
        page_size = 500 if max_messages is None else min(500, max_messages - len(ids))
        resp = service.users().messages().list(
            userId="me", q=query, pageToken=token, maxResults=page_size,
        ).execute()
        ids += [m["id"] for m in resp.get("messages", [])]
        token = resp.get("nextPageToken")
        if not token:
            break
    return ids


def existing_provider_ids(conn, user_id: str) -> set[str]:
    rows = conn.execute("SELECT provider_id FROM emails WHERE user_id = %s", (user_id,)).fetchall()
    return {r[0] for r in rows}

def get_message(service, mid, tries=5):
    for attempt in range(tries):
        try:
            return service.users().messages().get(userId="me", id=mid, format="full").execute()
        except HttpError as e:
            if e.status_code in (429, 500, 503) and attempt < tries - 1:
                time.sleep(2 ** attempt)          # wait 1s, 2s, 4s, 8s
                continue
            raise
def backfill(user_id: str, query: str, max_messages: int | None = None):
    service = get_gmail_read_service()
    conn = get_conn()

    have = existing_provider_ids(conn, user_id)
    ids = [i for i in list_message_ids(service, query, max_messages) if i not in have]
    total = len(ids)
    print(f"{total} new messages to import")

    saved = failed = 0
    start = time.time()
    for n, mid in enumerate(ids, 1):
        try:
            msg = get_message(service, mid)
            if save_email(conn, user_id, parse_message(msg)):
                saved += 1
        except HttpError as e:
            failed += 1
            print(f"Gmail error on {mid}: {e.status_code}")
        except Exception as e:
            failed += 1
            print(f"Failed on {mid}: {type(e).__name__}")    # never print email content

        if n % 20 == 0:
            rate = n / (time.time() - start)
            left = (total - n) / rate / 60
            print(f"  {n}/{total}  ({rate:.1f}/s, ~{left:.1f} min left)")

    print(f"done: saved={saved} failed={failed} in {(time.time() - start) / 60:.1f} min")

def get_history_id(conn, user_id):
    row = conn.execute("SELECT history_id FROM sync_state WHERE user_id = %s", (user_id,)).fetchone()
    return row[0] if row else None


def set_history_id(conn, user_id, history_id):
    conn.execute(
        """INSERT INTO sync_state (user_id, history_id) VALUES (%s, %s)
           ON CONFLICT (user_id) DO UPDATE SET history_id = EXCLUDED.history_id""",
        (user_id, str(history_id)),
    )


def start_watch(service, conn, user_id, topic):
    """Ask Gmail to publish to the topic. Expires after 7 days, so it is renewed daily."""
    resp = service.users().watch(
        userId="me",
        body={"topicName": topic, "labelIds": ["INBOX"], "labelFilterBehavior": "INCLUDE"},
    ).execute()
    if get_history_id(conn, user_id) is None:
        set_history_id(conn, user_id, resp["historyId"])


def import_ids(service, conn, user_id, ids, on_new=None):
    saved = failed = 0
    for mid in ids:
        try:
            parsed = parse_message(get_message(service, mid))
            if save_email(conn, user_id, parsed):
                saved += 1
                if on_new:
                    on_new(parsed)
        except HttpError as e:
            if e.status_code == 404:
                continue                      # deleted before we got to it
            failed += 1
            print(f"Gmail error on {mid}: {e.status_code}")
        except Exception as e:
            failed += 1
            print(f"Failed on {mid}: {type(e).__name__}")   # never print email content
    return saved, failed


def new_ids_since(service, start_history_id):
    ids, token, latest = [], None, start_history_id
    while True:
        resp = service.users().history().list(
            userId="me", startHistoryId=start_history_id,
            historyTypes=["messageAdded"], pageToken=token,
        ).execute()
        for h in resp.get("history", []):
            for m in h.get("messagesAdded", []):
                ids.append(m["message"]["id"])
        latest = resp.get("historyId", latest)
        token = resp.get("nextPageToken")
        if not token:
            break
    return list(dict.fromkeys(ids)), latest

def last_synced_epoch(conn, user_id: str) -> int | None:
    row = conn.execute(
        "SELECT max(sent_at) FROM emails WHERE user_id = %s", (user_id,)
    ).fetchone()
    return int(row[0].timestamp()) if row and row[0] else None


def sync_new(user_id: str, base_query: str = "-category:promotions -category:social"):
    """Date-based catch-up: fetch emails newer than the latest one already saved."""
    conn = get_conn()
    try:
        since = last_synced_epoch(conn, user_id)
    finally:
        conn.close()
    if since is None:
        raise RuntimeError("Nothing saved yet, run backfill first")

    # go back 1 day as a safety margin; already-saved ids are skipped before any work
    backfill(user_id, f"after:{since - 86400} {base_query}")


def sync_from_history(user_id, on_new=None):
    """Import everything that arrived since the stored historyId."""
    service = get_gmail_read_service()
    conn = get_conn()
    try:
        start = get_history_id(conn, user_id)
        if start is None:
            return
        try:
            ids, latest = new_ids_since(service, start)
        except HttpError as e:
            if e.status_code == 404:          # stored position too old, so catch up by date
                sync_new(user_id)
                profile = service.users().getProfile(userId="me").execute()
                set_history_id(conn, user_id, profile["historyId"])
                return
            raise

        have = existing_provider_ids(conn, user_id)
        ids = [i for i in ids if i not in have]
        failed = 0
        if ids:
            saved, failed = import_ids(service, conn, user_id, ids, on_new)
            print(f"new mail: saved={saved} failed={failed}")
        if failed == 0:
            set_history_id(conn, user_id, latest)
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    uid = os.environ["ADLER_USER_ID"]
    if len(sys.argv) > 1 and sys.argv[1] == "sync":
        sync_new(uid)
    else:
        backfill(uid, query="after:2023/01/01 -category:promotions -category:social")
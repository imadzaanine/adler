import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import pubsub_v1

from Helpers.get_gmail_service import get_credentials, READ_SCOPES, get_gmail_read_service
from database.db import get_conn
from mailhandler.ingest import start_watch, sync_from_history

load_dotenv()

PROJECT = os.environ["GCP_PROJECT"]
TOPIC = f"projects/{PROJECT}/topics/gmail-events"
SUBSCRIPTION = f"projects/{PROJECT}/subscriptions/gmail-events-sub"
USER_ID = os.environ["ADLER_USER_ID"]
HEARTBEAT = Path("heartbeat.txt")

sync_lock = threading.Lock()      # notifications can burst, run one sync at a time


def handle_new_email(email: dict):
    """Runs once per newly saved email. Keep it simple and rule-based for now."""
    print(f"New email saved ({email['sent_at']})")      # no subject or sender in logs


def sync():
    with sync_lock:
        sync_from_history(USER_ID, on_new=handle_new_email)
        HEARTBEAT.write_text(datetime.now(timezone.utc).isoformat())


def renew_watch_forever():
    while True:
        time.sleep(24 * 3600)
        try:
            conn = get_conn()
            start_watch(get_gmail_read_service(), conn, USER_ID, TOPIC)
            conn.close()
        except Exception as e:
            print("watch renew failed:", type(e).__name__)


def on_message(message):
    try:
        sync()
        message.ack()
    except Exception as e:
        print("sync failed:", type(e).__name__)
        message.nack()                                  # Pub/Sub will redeliver it


def run():
    creds = get_credentials(READ_SCOPES, "token_read.json")

    conn = get_conn()
    start_watch(get_gmail_read_service(), conn, USER_ID, TOPIC)
    conn.close()

    sync()                                              # catch up on anything missed while offline
    threading.Thread(target=renew_watch_forever, daemon=True).start()

    subscriber = pubsub_v1.SubscriberClient(credentials=creds)
    future = subscriber.subscribe(SUBSCRIPTION, callback=on_message)
    print("Listening for new mail...")
    try:
        future.result()
    except KeyboardInterrupt:
        future.cancel()


if __name__ == "__main__":
    run()
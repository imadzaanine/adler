import base64
from email.message import EmailMessage
from Helpers.get_gmail_service import get_gmail_service
from Helpers.get_gmail_service import get_calendar_service
from langchain_core.tools import tool
from datetime import datetime
from zoneinfo import ZoneInfo
from database.db import get_conn
from mailhandler.store import search
import os  
from dotenv import load_dotenv
import time


_conn = None

def _get_conn():
    global _conn
    if _conn is None or _conn.closed:
        _conn = get_conn()
    return _conn


load_dotenv()

@tool
def send_email(to: str, subject:str, body:str) -> str :
    """
    This function sends an email to the reciever

    Arg:

    to(str): the reciever who wil recieve the email
    subject(str): the subject of the email
    body(str): the content of the email

    Returns:
    
    the results of the excution

    """

    message = EmailMessage()

    service = get_gmail_service()

    message["To"] = to
    message["Subject"] = subject


    message.set_content(body)

    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()

    result = (
        service.users()
        .messages()
        .send(
            userId = "me",
            body = {"raw": encoded}
        )
        .execute()
    )

    return "The email has been sent"


@tool
def create_event_in_calendar( summary:str, description:str, startTime:str, endTime:str):
    """
    This tool creates an event in the calendar

    Arg:
    summary: a one line summary about the event
    description: the description of the event 
    startTime: the start time of the event (eg:2026-10-10T14:00:00+02:00)
    endTime: the end time of the event (eg:2026-10-10T15:00:00+02:00)

    Returns:
    the url that leads to the event in google calendar

    """
    calendar = get_calendar_service()

    event = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": startTime
        },
        "end": {
            "dateTime": endTime
            }
        
    }
    created_event = calendar.events().insert(
    calendarId="primary",
    body=event,
    ).execute()

    return "Event created:", created_event.get("htmlLink")

@tool
def get_current_time():
    """Returns the current date and time."""
    return datetime.now(ZoneInfo("Africa/Algiers")).isoformat()

@tool
def retrieve_from_email(query: str = "", after: str | None = None,
                        before: str | None = None, newest_first: bool = False,
                        limit: int = 5) -> str:
    """Search the user's emails.

    Args:
        query: topic, sender or keywords. Leave empty to list emails purely by date.
        after: only emails on or after this moment, ISO format with timezone,
               e.g. 2026-10-05T00:00:00+01:00
        before: only emails before this moment, same format.
        newest_first: set true when the user asks for the latest or most recent email.
        limit: how many emails to return (max 10).

    For relative dates such as "last week" or "yesterday", call get_current_time, then compute the range yourself.
    """
    limit = max(1, min(limit, 10))
    conn = _get_conn()
    results = search(conn, os.environ["ADLER_USER_ID"], query, limit, after, before, newest_first)

    if not results:
        return "No email matches"

    blocks = []
    for r in results:
        blocks.append(
            f"Email ID: {r['id']}\n"
            f"Date: {r['sent_at']}\n"
            f"From: {r['sender']}\n"
            f"Subject: {r['subject']}\n"
            f"Snippet: {r['snippet']}"
        )
    return "\n\n".join(blocks)

tools = [send_email, create_event_in_calendar, get_current_time, retrieve_from_email]
memory_tools = [get_current_time, retrieve_from_email]
email_tools = [send_email, get_current_time]
calendar_tools = [get_current_time, create_event_in_calendar]

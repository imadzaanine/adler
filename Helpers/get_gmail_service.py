import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SEND_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
]
READ_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/pubsub",
]


def get_credentials(scopes, token_file):
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", scopes)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            f.write(creds.to_json())
    return creds


def get_gmail_service():                 # sending (agent)
    return build("gmail", "v1", credentials=get_credentials(SEND_SCOPES, "token.json"))


def get_gmail_read_service():            # reading (ingestion only)
    return build("gmail", "v1", credentials=get_credentials(READ_SCOPES, "token_read.json"))


def get_calendar_service():
    return build("calendar", "v3", credentials=get_credentials(SEND_SCOPES, "token.json"))
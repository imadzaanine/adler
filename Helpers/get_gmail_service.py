import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


def get_gmail_service():
    """This function uses oaut2 to create a token and build the gmail API client"""
    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES  
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:

            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )
            creds = flow.run_local_server(port = 0)

        with open("token.json" , "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)





import base64
from email.message import EmailMessage
from Helpers.get_gmail_service import get_gmail_service
from langchain_core.tools import tool


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

tools = [send_email]
from langchain_core.messages import BaseMessage
from typing import TypedDict, Annotated, Sequence, Literal
from operator import add
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from pydantic import BaseModel


load_dotenv()




class AgentState(TypedDict):

    messages: Annotated[Sequence[BaseMessage], add]

    next_agent: Literal[
        "MEMORY",
        "EMAIL",
        "CALENDAR",
        "REFLECTION",
        "FINAL"
    ] | None


    # Reactive workflow control
    workflow_status: Literal[
        "RUNNING",
        "WAITING_FOR_USER",
        "COMPLETED"
    ]

    active_agent: Literal[
        "MEMORY",
        "EMAIL",
        "CALENDAR"
    ] | None


    pending_request: dict | None


    retrieved_context: dict | None

    email_result: dict | None

    calendar_result: dict | None


    reflection_result: dict | None


    final_response: str | None


    errors: list[str]


class SupervisorDecision(BaseModel):

    reasoning: str

    next_agent: Literal[
        "MEMORY",
        "EMAIL",
        "CALENDAR",
        "REFLECTION",
        "FINAL"
    ]


class AgentResult(BaseModel):

    status: Literal[
        "COMPLETED",
        "WAITING_FOR_USER",
        "FAILED"
    ]

    summary: str

    data: dict = {}

    missing_fields: list[str] = []


class MemoryResult(BaseModel):

    status: Literal[
        "COMPLETED",
        "FAILED"
    ]

    emails: list[dict]

    summary: str



class EmailResult(BaseModel):

    status: Literal[
        "COMPLETED",
        "WAITING_FOR_USER",
        "FAILED"
    ]

    recipient: str | None = None

    message_id: str | None = None

    summary: str

    missing_fields: list[str] = []



class CalendarResult(BaseModel):

    status: Literal[
        "COMPLETED",
        "WAITING_FOR_USER",
        "FAILED"
    ]

    event_id: str | None = None

    title: str | None = None

    start_time: str | None = None

    end_time: str | None = None

    summary: str

    missing_fields: list[str] = []



class ReflectionResult(BaseModel):

    status: Literal[
        "COMPLETE",
        "INCOMPLETE"
    ]

    reason: str



llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0
)


supervisor_llm = llm.with_structured_output(
    SupervisorDecision
)


reflection_llm = llm.with_structured_output(
    ReflectionResult
)


response_llm = llm
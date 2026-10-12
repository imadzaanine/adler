from langchain_core.messages import BaseMessage, HumanMessage
from typing import TypedDict, Annotated, Sequence,Literal
from operator import add 
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from Nodes.tools import memory_tools, email_tools, calendar_tools
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
    task_plan: list[str]
    completed_tasks: Annotated[list[str],add]
    retrieved_context: dict
    email_result : dict
    calendar_result: dict
    reflection: str | None
    error: list[str]



class SupervisorDecision(BaseModel):
    next_agent: Literal[
        "MEMORY",
        "EMAIL",
        "CALENDAR",
        "REFLECTION",
        "FINAL"
    ]

class MemoryRetrieval(BaseModel):
    retrieved_context: dict

class EmailResult(BaseModel):
    success: bool
    recipient: str | None
    message_id: str | None
    summary: str

class CalendarResult(BaseModel):
    success: bool
    event_id: str | None
    title: str | None
    start_time: str | None
    end_time: str | None
    summary: str


llm = ChatGroq(model = "openai/gpt-oss-120b",
               temperature=0)


supervisor_llm = llm.with_structured_output(
    SupervisorDecision
    )
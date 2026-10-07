from langchain_core.messages import BaseMessage
from typing import TypedDict, Annotated, Sequence
from operator import add as add_messages
from dotenv import load_dotenv
from langchain_groq import ChatGroq



load_dotenv()

llm = ChatGroq(model = "openai/gpt-oss-120b",
               temperature=0)

class AgentState(TypedDict):
    message: Annotated[Sequence[BaseMessage], add_messages]
from dotenv import load_dotenv
load_dotenv()
import os
from langgraph.graph import StateGraph, START,END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage
from state import AgentState
from Nodes.supervisor import Supervisor_node
from Nodes.memory import Memory_Agent_node
from Nodes.email_agent import Email_Agent_node
from Nodes.calendar_agent import Calendar_Agent_node
from Nodes.Reflection import Reflection_Agent_node
from Nodes.Response import Response_Agent_node
from Nodes.tools import tools
from Helpers.supervisor_edge_helper import supervisor_router
from langgraph.prebuilt import ToolNode



memory = MemorySaver()

graph = StateGraph(AgentState)

graph.add_node("Supervisor", Supervisor_node)
graph.add_node("Memory",Memory_Agent_node )
graph.add_node("Email_Agent",Email_Agent_node)
graph.add_node("Calendar_Agent",Calendar_Agent_node)
graph.add_node("Reflection_Agent", Reflection_Agent_node)
graph.add_node("Response_Agent", Response_Agent_node)



graph.add_edge(START,"Supervisor")

graph.add_edge("Memory","Supervisor")
graph.add_edge("Email_Agent", "Supervisor")
graph.add_edge("Calendar_Agent", "Supervisor")
graph.add_edge("Response_Agent", END)

graph.add_conditional_edges("Supervisor",
                            supervisor_router,
                            {
                            "memory_agent": "Memory",
                            "email_agent": "Email_Agent",
                            "calendar_agent": "Calendar_Agent",
                            "reflection_agent": "Reflection_Agent",
                            "response_agent": "Response_Agent"
                        })

app = graph.compile(checkpointer = memory)



config = {
    "configurable":{
    "thread_id":"commander",
    "user_id": os.environ["ADLER_USER_ID"]
    }
}

result = app.invoke(
    {
                "messages": [
                    HumanMessage("When did Mr.khalfi message me")
                ]
            },
            config=config
)









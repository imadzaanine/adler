from dotenv import load_dotenv
load_dotenv()

import os

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

from state import AgentState

from Nodes.supervisor import Supervisor_node
from Nodes.memory import Memory_Agent_node
from Nodes.email_agent import Email_Agent_node
from Nodes.calendar_agent import Calendar_Agent_node
from Nodes.reflection import Reflection_Agent_node
from Nodes.response import Response_Agent_node

from Helpers.supervisor_edge_helper import supervisor_router
from Helpers.reflection_edge_helper import reflection_router


# -------------------------
# Build graph
# -------------------------

memory = MemorySaver()

graph = StateGraph(AgentState)


graph.add_node(
    "Supervisor",
    Supervisor_node
)

graph.add_node(
    "Memory",
    Memory_Agent_node
)

graph.add_node(
    "Email_Agent",
    Email_Agent_node
)

graph.add_node(
    "Calendar_Agent",
    Calendar_Agent_node
)

graph.add_node(
    "Reflection_Agent",
    Reflection_Agent_node
)

graph.add_node(
    "Response_Agent",
    Response_Agent_node
)


# -------------------------
# Edges
# -------------------------

graph.add_edge(
    START,
    "Supervisor"
)

graph.add_edge(
    "Memory",
    "Supervisor"
)

graph.add_edge(
    "Email_Agent",
    "Supervisor"
)

graph.add_edge(
    "Calendar_Agent",
    "Supervisor"
)

graph.add_edge(
    "Response_Agent",
    END
)


graph.add_conditional_edges(
    "Supervisor",
    supervisor_router,
    {
        "memory_agent": "Memory",
        "email_agent": "Email_Agent",
        "calendar_agent": "Calendar_Agent",
        "reflection_agent": "Reflection_Agent",
        "response_agent": "Response_Agent",
    }
)


graph.add_conditional_edges(
    "Reflection_Agent",
    reflection_router,
    {
        "response_agent": "Response_Agent",
        "supervisor": "Supervisor",
    }
)


app = graph.compile(
    checkpointer=memory
)



# -------------------------
# Config
# -------------------------

config = {
    "configurable": {
        "thread_id": "commander",
        "user_id": os.environ["ADLER_USER_ID"],
    },
    "recursion_limit": 50,
}



# -------------------------
# First message
# -------------------------

def first_turn(text: str) -> dict:

    return {

        "messages": [
            HumanMessage(content=text)
        ],

        "next_agent": None,

        "workflow_status": "RUNNING",

        "active_agent": None,

        "pending_request": None,

        "retrieved_context": None,

        "email_result": None,

        "calendar_result": None,

        "reflection_result": None,

        "final_response": None,

        "errors": [],

    }



# -------------------------
# Continue conversation
# -------------------------

def continue_turn(text: str, previous_state: dict) -> dict:

    update = {

        "messages": [
            HumanMessage(content=text)
        ]

    }


    # Resume the agent that was waiting
    if previous_state.get("workflow_status") == "WAITING_FOR_USER":

        waiting_agent = previous_state.get(
            "active_agent"
        )


        if waiting_agent:

            update["workflow_status"] = "RUNNING"

            update["next_agent"] = waiting_agent

            update["active_agent"] = None

            update["pending_request"] = None


    return update



# -------------------------
# CLI
# -------------------------

initialized = False


while True:

    user_input = input("\nCommander: ").strip()


    if not user_input:
        continue


    if user_input.lower() in {
        "exit",
        "quit"
    }:
        break


    try:

        # Get previous checkpoint state
        checkpoint = app.get_state(config)


        previous_state = (
            checkpoint.values
            if checkpoint
            else {}
        )


        if not previous_state:

            payload = first_turn(
                user_input
            )

        else:

            payload = continue_turn(
                user_input,
                previous_state
            )


        result = app.invoke(
            payload,
            config=config
        )


        print(
            "\nA.L.D.R:",
            result.get(
                "final_response",
                ""
            )
        )


    except KeyboardInterrupt:

        print(
            "\n(cancelled)"
        )


    except Exception as e:

        print(
            f"\nA.L.D.R: error ({type(e).__name__}): {e}"
        )
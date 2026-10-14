from datetime import datetime
from zoneinfo import ZoneInfo

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, ToolMessage

from state import AgentState, llm
from Nodes.tools import calendar_tools
from Helpers.context_message import context_message



SYSTEM_PROMPT = """
You are the Calendar Agent.

Your only responsibility is creating calendar events.

You do not:
- decide workflow
- answer users
- send emails
- retrieve emails


Tool:
create_event_in_calendar


Rules:

Defaults:
- Duration: 1 hour
- Optional location and description can be omitted

Required:
- A date
- A time

If the date or time cannot be determined:
Return that information is missing.

Never invent dates or times.


After creating an event:
Return:
- title
- date
- time
- attendee
- event link
"""


calendar_agent = create_agent(
    model=llm,
    tools=calendar_tools,
    system_prompt=SYSTEM_PROMPT
)



def Calendar_Agent_node(state: AgentState) -> dict:


    now = datetime.now(
        ZoneInfo("Africa/Algiers")
    )


    date_msg = HumanMessage(
        content=
        f"[Current date and time: "
        f"{now.strftime('%A %Y-%m-%d %H:%M')} UTC+1]"
    )


    msgs = [
        *state["messages"],
        date_msg
    ]


    ctx = context_message(state)

    if ctx:
        msgs.append(ctx)


    response = calendar_agent.invoke(
        {
            "messages": msgs
        }
    )


    final_message = response["messages"][-1]


    created = any(
        isinstance(m, ToolMessage)
        and m.name == "create_event_in_calendar"
        and getattr(m, "status", "success") != "error"
        and "Event created" in str(m.content)
        for m in response["messages"]
    )


    if created:

        return {

            "calendar_result": {
                "status": "COMPLETED",
                "summary": str(final_message.content),
                "missing_fields": []
            },

            "workflow_status": "RUNNING",

            "active_agent": None,

            "pending_request": None
        }



    return {

        "calendar_result": {
            "status": "WAITING_FOR_USER",
            "summary": str(final_message.content),
            "missing_fields": [
                "date_or_time"
            ]
        },


        "workflow_status": "WAITING_FOR_USER",

        "active_agent": "CALENDAR",

        "pending_request": {

            "agent": "CALENDAR",

            "missing_fields": [
                "date_or_time"
            ]

        }
    }
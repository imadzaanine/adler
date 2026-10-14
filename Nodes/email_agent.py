from state import AgentState, llm
from Nodes.tools import email_tools
from langchain.agents import create_agent
from langchain_core.messages import ToolMessage
from Helpers.context_message import context_message


SYSTEM_PROMPT = """
You are the Email Agent in a multi-agent AI system.

You only handle email actions assigned by the Supervisor.

You do not:
- decide workflow
- call other agents
- answer the user directly


Tool:
send_email

Rules:

- Use retrieved context when available.
- Never invent email addresses or facts.
- For replies, use "Re: <original subject>".
- Optional information like agenda, location, links is not required.

Required information:
- Recipient
- Email content/body

If required information is missing:
Do NOT pretend the email was sent.
Return a clear message explaining what is missing.

After completing:
Return a short summary of the action.
"""


email_agent = create_agent(
    model=llm,
    tools=email_tools,
    system_prompt=SYSTEM_PROMPT
)


def Email_Agent_node(state: AgentState) -> dict:

    msgs = list(state["messages"])

    ctx = context_message(state)

    if ctx:
        msgs.append(ctx)


    response = email_agent.invoke(
        {
            "messages": msgs
        }
    )


    final_message = response["messages"][-1]


    sent = any(
        isinstance(m, ToolMessage)
        and m.name == "send_email"
        and getattr(m, "status", "success") != "error"
        for m in response["messages"]
    )


    if sent:

        return {
            "email_result": {
                "status": "COMPLETED",
                "summary": str(final_message.content),
                "missing_fields": []
            },

            "workflow_status": "RUNNING",
            "active_agent": None,
            "pending_request": None
        }


    # Agent decided information is missing
    return {
        "email_result": {
            "status": "WAITING_FOR_USER",
            "summary": str(final_message.content),
            "missing_fields": [
                "required_email_information"
            ]
        },

        "workflow_status": "WAITING_FOR_USER",

        "active_agent": "EMAIL",

        "pending_request": {
            "agent": "EMAIL",
            "missing_fields": [
                "required_email_information"
            ]
        }
    }
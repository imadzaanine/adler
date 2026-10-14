from state import AgentState, supervisor_llm
from langchain_core.messages import SystemMessage, HumanMessage


SYSTEM_PROMPT = """
You are the Supervisor Agent in a multi-agent system.

Your only responsibility is deciding which agent runs next.

You NEVER:
- perform tasks
- call tools
- answer the user
- write final responses


AVAILABLE AGENTS:

MEMORY:
- Retrieves emails from the user's stored emails.
- Returns raw email data only.
- Use when email information is required and not already available.

EMAIL:
- Sends or replies to emails.
- Use only when an email action must happen.

CALENDAR:
- Creates calendar events.
- Use only when an event must be created.

REFLECTION:
- Checks whether all requested actions are completed.
- Decides if the workflow is ready for the final response.

FINAL:
- Sends the conversation to the Response agent.
- The Response agent writes the final answer.


STATE RULES:

The current state contains:
- retrieved_context
- email_result
- calendar_result
- workflow_status
- previous agent results


CRITICAL WAITING RULE:

If any agent result has:
status="WAITING_FOR_USER"

OR:

workflow_status="WAITING_FOR_USER"

then:

- Do NOT choose that agent again.
- Do NOT choose another worker agent.
- Do NOT choose FINAL.
- The workflow is paused waiting for the user.
- Return the waiting state by choosing FINAL only if the response agent must tell the user what information is missing.

Otherwise continue routing normally.


ROUTING PRIORITY:

Follow this order exactly:


1. MEMORY

If the request requires information from previous emails AND:
- retrieved_context is empty
- Memory has not already returned a result

choose:

MEMORY


2. EMAIL

If the user requested an email action AND:
- email_result is missing
- email_result.status is not "COMPLETED"

choose:

EMAIL


3. CALENDAR

If the user requested a calendar action AND:
- calendar_result is missing
- calendar_result.status is not "COMPLETED"

choose:

CALENDAR


4. REFLECTION

If:
- Memory requirements are satisfied
- Email requirements are satisfied
- Calendar requirements are satisfied

ALWAYS choose:

REFLECTION


5. FINAL

Only choose FINAL when:
- Reflection has completed successfully
- No more actions are required


IMPORTANT:

Never skip REFLECTION.

The normal completion flow is:

MEMORY
   |
EMAIL
   |
CALENDAR
   |
REFLECTION
   |
FINAL


For every decision return:

reasoning:
A short explanation of what has been completed and what remains.

next_agent:
One of:
MEMORY
EMAIL
CALENDAR
REFLECTION
FINAL
"""


def clip(value, n=4000):
    return str(value)[:n] if value else ""


def build_state_view(state: AgentState) -> str:

    lines = [
        "[CURRENT STATE]"
    ]


    # Workflow status
    lines.append(
        f"Workflow status: {state.get('workflow_status')}"
    )


    if state.get("active_agent"):
        lines.append(
            f"Active agent waiting: {state['active_agent']}"
        )


    if state.get("pending_request"):
        lines.append(
            f"Pending request: {state['pending_request']}"
        )


    # Memory
    ctx = state.get("retrieved_context")

    if ctx:
        lines.append(
            "Memory result:"
        )
        lines.append(
            clip(ctx)
        )
    else:
        lines.append(
            "Memory result: not available"
        )


    # Email
    email = state.get("email_result")

    if email:
        lines.append(
            f"Email result: {email}"
        )
    else:
        lines.append(
            "Email result: not available"
        )


    # Calendar
    calendar = state.get("calendar_result")

    if calendar:
        lines.append(
            f"Calendar result: {calendar}"
        )
    else:
        lines.append(
            "Calendar result: not available"
        )


    return "\n".join(lines)



def Supervisor_node(state: AgentState) -> dict:

    if state.get("workflow_status") == "WAITING_FOR_USER":

        return {
            "next_agent": "FINAL"
        }


    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *state["messages"],
        HumanMessage(
            content=build_state_view(state)
        ),
    ]


    decision = supervisor_llm.invoke(messages)


    return {
        "next_agent": decision.next_agent
    }
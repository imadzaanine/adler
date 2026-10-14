from state import AgentState, reflection_llm
from langchain_core.messages import SystemMessage


SYSTEM_PROMPT = """
You are the Reflection Agent in a multi-agent AI system.

Your job is to verify whether the user's request has been fully completed.

You do not execute tasks.
You do not use tools.
You do not communicate with the user.

You only analyze the current state.

Check:

- Email result
- Calendar result
- Retrieved context
- Any errors


Rules:

Return COMPLETE only when:
- All requested actions succeeded.
- No required information is missing.
- No agent action remains.


Return INCOMPLETE when:
- A requested action failed.
- A required action has not happened.
- More information is needed.


Return:

status:
COMPLETE or INCOMPLETE

reason:
A short explanation.
"""


def Reflection_Agent_node(state: AgentState) -> dict:


    messages = [

        SystemMessage(
            content=SYSTEM_PROMPT
        ),

        *state["messages"],


        SystemMessage(
            content=f"""
CURRENT STATE:

Retrieved context:
{state.get("retrieved_context")}


Email result:
{state.get("email_result")}


Calendar result:
{state.get("calendar_result")}


Errors:
{state.get("errors")}
"""
        )
    ]


    result = reflection_llm.invoke(
        messages
    )


    return {

        "reflection_result": {

            "status": result.status,

            "reason": result.reason

        }

    }
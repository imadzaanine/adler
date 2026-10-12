from state import AgentState, llm
from Nodes.tools import memory_tools
from langchain.agents import create_agent
from langchain_core.messages import SystemMessage,HumanMessage

SYSTEM_PROMPT = """

You are the Memory Agent.

Your job is to retrieve relevant information from the user's stored emails.

You have access to:
- retrieve_from_email
- get_current_time

When the user asks about previous conversations:
1. Analyze the user's request.
2. Use retrieve_from_email to find relevant information.
3. Summarize the retrieved information.
4. Store useful context for other agents.

Do not send emails.
Do not create calendar events.
Only retrieve and summarize information.

"""
memory_agent = create_agent(
    model=llm,
    tools=memory_tools,
    system_prompt=SYSTEM_PROMPT
)



def Memory_Agent_node(state: AgentState) -> dict:

    result = memory_agent.invoke(
        {
            "messages": state["messages"]
        }
    )

    final_message = result["messages"][-1]

    return {
        "retrieved_context": {
            "information": final_message.content
        },
        "completed_tasks": [
            "memory_completed"
        ]
    }

if __name__=="__main__":
    state = AgentState(messages=
                       [HumanMessage("get djiali's email address and send him an email about a meeting and add it to my calendar")])

    result = Memory_Agent_node(state)

    print(result)
from state import AgentState


def should_continue(state:AgentState):
    """A helper function to guide the processing node to know if there is no more tools to call and go to the end"""
    messages = state["messages"]
    last_message = messages[-1]

    if not last_message.tool_calls:
        return "end"
    else:
        return "continue"
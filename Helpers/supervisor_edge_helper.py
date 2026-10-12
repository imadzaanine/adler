from state import AgentState

def supervisor_router(state: AgentState):

    next_agent = state.get("next_agent")

    if next_agent == "MEMORY":
        return "memory_agent"

    elif next_agent == "EMAIL":
        return "email_agent"

    elif next_agent == "CALENDAR":
        return "calendar_agent"

    elif next_agent == "REFLECTION":
        return "reflection_agent"

    elif next_agent == "FINAL":
        return "response_agent"

    else:
        raise ValueError(
            f"Unknown next agent: {next_agent}"
        )
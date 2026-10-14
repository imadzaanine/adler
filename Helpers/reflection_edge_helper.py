from state import AgentState


def reflection_router(state: AgentState):

    reflection = state.get("reflection_result")


    if not reflection:
        return "supervisor"


    status = reflection.get("status")


    if status == "COMPLETE":
        return "response_agent"


    elif status == "INCOMPLETE":
        return "supervisor"
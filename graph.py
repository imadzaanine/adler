from langgraph.graph import StateGraph, START, END
from Nodes.processing import processing_node
from state import AgentState
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
graph = StateGraph(AgentState)

graph.add_node("processing", processing_node)

graph.add_edge(START,"processing")
graph.add_edge("processing" ,END)

app = graph.compile(checkpointer = memory)



config = {
    "configurable":{
    "thread_id":"commander"
    }
}

while True:
    user_input = input("\nCommander: ")

    if user_input.lower() in {"exit", "quit"}:
        break

    result = app.invoke(
        {
            "message": [
                HumanMessage(content=user_input)
            ]
        },
        config=config
    )

    print("A.L.D.R:", result["message"][-1].content)


from langgraph.graph import StateGraph, START, END
from Nodes.processing import processing_node
from state import AgentState
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from Nodes.tools import tools
from Helpers.should_continue import should_continue

memory = MemorySaver()
graph = StateGraph(AgentState)

graph.add_node("processing", processing_node)

tool_node = ToolNode(tools = tools)
graph.add_node("tools", tool_node)


graph.add_edge(START,"processing")


graph.add_conditional_edges("processing",
                            should_continue,{
                                "continue": "tools",
                                "end": END
                            })

graph.add_edge("tools", "processing")

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
            "messages": [
                HumanMessage(content=user_input)
            ]
        },
        config=config
    )

    print("A.L.D.R:", result["messages"][-1].content)


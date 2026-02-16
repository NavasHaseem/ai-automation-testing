from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

# Import your nodes
from tools.pinecone_tool import pinecone_retrieval_tool  
from ai_agents.context_agent_node import context_reasoning_node
from ai_agents.testcase_agent_node import testcase_generator_node
 
from states.base_state import AgentState, JiraStory

# -----------------------------
# Initialize nodes
# -----------------------------
# pinecone_node = pinecone_retrieval_tool()
# reasoning_node = context_reasoning_node()

def build_context_agent_graph():
    graph_builder = StateGraph(AgentState)

    # Nodes
    graph_builder.add_node(
        "pinecone_retrieval",
          pinecone_retrieval_tool)
    

    graph_builder.add_node(
        "context_reasoning",
        context_reasoning_node
    )

    graph_builder.add_node("TestCase_generator", testcase_generator_node)


    # Edges (NO conditional edges)
    graph_builder.add_edge(START, "pinecone_retrieval")
    graph_builder.add_edge("pinecone_retrieval", "context_reasoning")
    graph_builder.add_edge("context_reasoning", "TestCase_generator")
    graph_builder.add_edge("TestCase_generator", END)

    graph = graph_builder.compile()
    return graph


def build_context_graph():
    graph_builder = StateGraph(AgentState)

    graph_builder.add_node(
        "pinecone_retrieval",
        pinecone_retrieval_tool
    )

    graph_builder.add_node(
        "context_reasoning",
        context_reasoning_node
    )

    graph_builder.add_edge(START, "pinecone_retrieval")
    graph_builder.add_edge("pinecone_retrieval", "context_reasoning")
    graph_builder.add_edge("context_reasoning", END)

    return graph_builder.compile()


def build_testcase_graph():
    graph_builder = StateGraph(AgentState)

    graph_builder.add_node(
        "testcase_generator",
        testcase_generator_node
    )

    graph_builder.add_edge(START, "testcase_generator")
    graph_builder.add_edge("testcase_generator", END)

    return graph_builder.compile()

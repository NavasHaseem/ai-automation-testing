from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone
import os
import openai
from langchain_openai import ChatOpenAI

load_dotenv()
openai_key = os.getenv("OPENAI_API_KEY")




llm = ChatOpenAI(model="gpt-4o-mini")
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))



index = pc.Index(name=os.getenv("PINECONE_INDEX_NAME"))


client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class RepoState(TypedDict):
    analysis_result: Optional[str]
    pinecone_index: any
    openai_client: any
    llm: any


def group_chunks_by_metadata(matches):
    grouped = {}

    for match in matches:
        meta = match.metadata
        key = (
            meta.get("branch"),
            meta.get("first_line_after_branch")
        )

        if key not in grouped:
            grouped[key] = {
                "metadata": meta,
                "chunks": []
            }

        grouped[key]["chunks"].append(meta.get("text", ""))

    return grouped

def project_analysis_agent_node(state: RepoState) -> RepoState:
    index = state["pinecone_index"]
    llm = state["llm"]
    client = state["openai_client"]

    embedding = client.embeddings.create(
        model="text-embedding-3-large",
        input="project architecture build dependencies",
        dimensions=1024
    ).data[0].embedding

    results = index.query(
        namespace="github-repos-test",
        vector=embedding,
        top_k=5,
        include_metadata=True
    )

    grouped_chunks = group_chunks_by_metadata(results.matches)

    # ✅ Take ONLY the first metadata group
    first_group = next(iter(grouped_chunks.values()), None)

    if not first_group:
        return {
            **state,
            "analysis_result": "No matching README chunks found"
        }

    metadata = first_group["metadata"]
    chunks = first_group["chunks"]

    combined_text = "\n\n".join(chunks)

    prompt = f"""
    You are a senior automation architect.

    {combined_text}

    Extract project build and dependencies in JSON.
    """

    response = llm.invoke(prompt)

    return {
        **state,
        "analysis_result": response.content
    }








def build_analysis_graph():
    graph = StateGraph(RepoState)

    graph.add_node("ProjectAnalysisAgent", project_analysis_agent_node)
    graph.set_entry_point("ProjectAnalysisAgent")
    graph.add_edge("ProjectAnalysisAgent", END)

    return graph.compile()





graph = build_analysis_graph()

result = graph.invoke({
    "pinecone_index": index,
    "openai_client": client,
    "llm": llm
})

print(result["analysis_result"])

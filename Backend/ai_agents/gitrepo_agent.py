from typing import TypedDict, Optional, List
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
from pinecone import Pinecone
import os
import openai
from langchain_openai import ChatOpenAI
import pandas as pd
import json

 # Import the analysis graph builder from app.py
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
    analysis_result : Optional[str]
    excel_path: str
    row_queries: List[str]
    generated_responses: List[str]
    current_index: int


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
        namespace="github-repos-test-2",
        vector=embedding,
        top_k=5,
        include_metadata=True
    )

    grouped_chunks = group_chunks_by_metadata(results.matches)

    # Take ONLY the first metadata group
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



import pandas as pd

def load_excel_queries(excel_path: str) -> list[dict]:
    df = pd.read_excel(excel_path)

    # Remove completely empty rows
    df = df.dropna(how="all")

    # Convert each row into dictionary
    records = df.to_dict(orient="records")

    return records

def should_continue_excel(state: RepoState):

    if state["current_index"] >= len(state["row_queries"]):
        return END

    return "ExcelIterationAgent"





def excel_iteration_agent_node(state: RepoState) -> RepoState:

    llm = state["llm"]
    excel_path = state["excel_path"]
    analysis_prompt = state["analysis_result"]

    if "row_queries" not in state:
        queries = load_excel_queries(excel_path)
        state["row_queries"] = queries
        state["current_index"] = 0
        state["generated_responses"] = []

    queries = state["row_queries"]
    idx = state["current_index"]

    if idx >= len(queries):
        return state

    current_query = queries[idx]
    test_data = current_query.get("Test Data", "")

    current_query_text = json.dumps(current_query, indent=2)

    final_prompt = f"""
    You are a senior automation architect.Based upon the below analysis generate the the style and create code explicitly for new tests.
    Don't give any other explanation except the code. Just give the code.

    Context from previous analysis:
    {analysis_prompt}

    Test Data should be compulsiorly used dynamically in test:
    {test_data}

    The test data may represent name, password, product name, flight route, etc.
    Use test data compulsory and correctly in feature file, step definitions, service layer and page object.

    It should have the Layered UI automation test architecture like the belwo example:
    Cucumber (BDD)
    ↓
    Step Definitions (Java)
    ↓
    Service Layer
    ↓
    Playwright Page Objects
    ↓
    Test Context from {test_data} should be used in all layers of the test.

    Now answer:
    {current_query_text}
    """

    response = llm.invoke(final_prompt)

    state["generated_responses"].append(response.content)
    state["current_index"] += 1

    return state


def build_analysis_graph():

    graph_1 = StateGraph(RepoState)

    graph_1.add_node("ProjectAnalysisAgent", project_analysis_agent_node)
    graph_1.add_node("ExcelIterationAgent", excel_iteration_agent_node)

    graph_1.set_entry_point("ProjectAnalysisAgent")

    graph_1.add_edge("ProjectAnalysisAgent", "ExcelIterationAgent")

    graph_1.add_conditional_edges(
        "ExcelIterationAgent",
        should_continue_excel,
        {
            END: END,
            "ExcelIterationAgent": "ExcelIterationAgent"
        }
    )

    return graph_1.compile()


# state.py
from typing import TypedDict, Optional
# embedding_tools.py
from dotenv import load_dotenv
import os
import subprocess
import logging
from langchain_openai import ChatOpenAI
from openai import OpenAI
import pinecone
from pinecone import Pinecone
import openai

load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY")




llm = ChatOpenAI(model="gpt-4o-mini")
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))



index = pc.Index(name=os.getenv("PINECONE_INDEX_NAME"))


client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# state.py
from typing import TypedDict, Optional



class RepoState(TypedDict):
    repo_url: str
    readme_context: Optional[str]   # combined README content
    embedding_status: Optional[str]



# repo_tools.py
import os
import subprocess


def run_cmd(cmd, cwd=None):
    result = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True
    )
    return result.stdout.strip()
def embed_and_store_readme(
    content: str,
    metadata_line: str,
    index
):
    embedding = client.embeddings.create(
        model="text-embedding-3-large",
        input=content,
        dimensions=1024
    ).data[0].embedding

    index.upsert(
        vectors=[{
            "id": metadata_line[:50],   # safe ID
            "values": embedding,
            "metadata": {
                "source": "README.md",
                "branch_context": metadata_line
            }
        }],
        namespace="github-repos-test"
    )

def clone_repo(repo_url: str, base_dir: str = "C:/Users/abishek.h/Documents/Cloned_Repos") -> str:
    os.makedirs(base_dir, exist_ok=True)

    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    repo_path = os.path.join(base_dir, repo_name)

    if not os.path.exists(repo_path):
        run_cmd(["git", "clone", "-b", "master", repo_url, repo_path])

    return repo_path


def get_all_branches(repo_path: str) -> list[str]:
    run_cmd(["git", "fetch", "--all"], cwd=repo_path)

    output = run_cmd(["git", "branch", "-a"], cwd=repo_path)

    branches = set()
    for line in output.splitlines():
        line = line.strip()
        if "HEAD" in line:
            continue
        line = line.replace("*", "").strip()
        if line.startswith("remotes/origin/"):
            line = line.replace("remotes/origin/", "")
        branches.add(line)

    return list(branches)


def checkout_branch(repo_path: str, branch: str):
    try:
        run_cmd(["git", "checkout", branch], cwd=repo_path)
    except subprocess.CalledProcessError:
        run_cmd(["git", "checkout", "-b", branch, f"origin/{branch}"], cwd=repo_path)


def read_readme(repo_path: str) -> str | None:
    readme_path = os.path.join(repo_path, "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    return None



# repo_agent.py
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def repo_agent_node(state: RepoState) -> RepoState:
    repo_url = state["repo_url"]

    repo_path = clone_repo(repo_url)
    branches = get_all_branches(repo_path)

    readme_context = []

    for branch in branches:
        checkout_branch(repo_path, branch)
        content = read_readme(repo_path)

        if content:
            readme_context.append(
                f"### Branch: {branch}\n{content}"
            )

    combined_context = "\n\n".join(readme_context)

    return {
        "repo_url": repo_url,
        "readme_context": combined_context
    }

# embedding_agent.py
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def embedding_agent_node(state: RepoState) -> RepoState:
    readme_context = state.get("readme_context")

    if not readme_context:
        return {
            **state,
            "embedding_status": "❌ No README content to embed"
        }

    # ---- Extract MASTER README ----
    sections = readme_context.split("### Branch:")
    master_section = None

    for section in sections:
        if section.strip().startswith("master"):
            master_section = section
            break

    if not master_section:
        return {
            **state,
            "embedding_status": "⚠️ Master README not found"
        }

    lines = master_section.splitlines()

    # ---- First meaningful line after branch name ----
    metadata_line = None
    for line in lines[1:]:
        if line.strip():
            metadata_line = line.strip()
            break

    if not metadata_line:
        metadata_line = "Master README"

    # ---- Embed & store ----
    embed_and_store_readme(
        content=master_section,
        metadata_line=metadata_line,
        index=index   
    )

    return {
        **state,
        "embedding_status": " README embedded successfully"
    }



def build_graph():
    graph = StateGraph(RepoState)

    graph.add_node("RepoAgent", repo_agent_node)
    graph.add_node("EmbeddingAgent", embedding_agent_node)

    graph.set_entry_point("RepoAgent")
    graph.add_edge("RepoAgent", "EmbeddingAgent")
    graph.add_edge("EmbeddingAgent", END)

    return graph.compile()



app = build_graph()

result = app.invoke({
    "repo_url": "https://github.com/Hemashree-s98/UI_Framework.git"
})

print("\n FINAL STATUS")
print("Embedding:", result["embedding_status"])

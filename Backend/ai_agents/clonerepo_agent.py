from typing import TypedDict, Optional
from dotenv import load_dotenv
import os
import subprocess
from langchain_openai import ChatOpenAI
from pinecone import Pinecone
import openai
from langgraph.graph import StateGraph, END


load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-4o-mini")
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(name=os.getenv("PINECONE_INDEX_NAME"))
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# state.py



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
        namespace="github-repos-test-1"
    )

def clone_repo(repo_url: str, base_dir: str = "Cloned_Repos") -> str:
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








def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50):
    words = text.split()
    chunks = []

    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap

    return chunks

def embed_and_upload(content: str, branch: str):

    chunks = chunk_text(content)
    vectors = []

    for i, chunk in enumerate(chunks):

        embedding = client.embeddings.create(
            model="text-embedding-3-large",
            input=chunk,
            dimensions=1024
        ).data[0].embedding

        vectors.append({
            "id": f"{branch}-{i}",
            "values": embedding,
            "metadata": {
                "branch": branch,
                "source": "README.md",
                "first_50_chars": chunk[:50],
                "text": chunk
            }
        })

    if vectors:
        index.upsert(
            vectors=vectors,
            namespace="github-repos-test-1"
        )


class RepoState(TypedDict):
    repo_url: str
    readme_context: str
    embedding_status: str

 #Agent 1: Repo Cloning & README Extraction   
def repo_agent_node(state: RepoState) -> RepoState:

    repo_url = state["repo_url"]

    repo_path = clone_repo(repo_url)
    branches = get_all_branches(repo_path)

    readme_context = []

    for branch in branches:

        checkout_branch(repo_path, branch)
        content = read_readme(repo_path)

        if not content:
            continue

        readme_context.append(
            f"### Branch: {branch}\n{content}"
        )

        # 🔥 Embed and upload
        embed_and_upload(
            content=content,
            branch=branch
        )

    combined_context = "\n\n".join(readme_context)

    return {
        **state,
        "readme_context": combined_context
        #"embedding_status": "README embedded & uploaded successfully"
    }


def build_embed_graph():
    graph_2 = StateGraph(RepoState)

    graph_2.add_node("RepoAgent", repo_agent_node)

    graph_2.set_entry_point("RepoAgent")
    graph_2.add_edge("RepoAgent", END)

    return graph_2.compile()


# def build_graph():
#     graph = StateGraph(RepoState)

#     graph.add_node("RepoAgent", repo_agent_node)

#     graph.set_entry_point("RepoAgent")
#     graph.add_edge("RepoAgent", END)

#     return graph.compile()



# app = build_graph()

# result = app.invoke({
#    # "repo_url": repo_url #"https://github.com/Hemashree-s98/UI_Framework.git",
#     "repo_url": "https://github.com/Hemashree-s98/UI_Framework.git"

# })

# print("\n FINAL STATUS")
# print("Embedding:", result["embedding_status"])



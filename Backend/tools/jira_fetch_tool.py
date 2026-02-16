from typing import List, Dict, Any, Iterable
from agents.mcp.server import MCPServerStdio
import os
import re
import json 
from rapidfuzz import fuzz
from dotenv import load_dotenv

load_dotenv()

 
MCP_COMMAND = os.environ.get("MCP_COMMAND", "uvx")  # e.g., "uvx" in PATH
MCP_ARGS = os.environ.get("MCP_ARGS", "mcp-atlassian").split()  
CONFLUENCE_API_TOKEN = (os.environ.get("CONFLUENCE_API_TOKEN") or "").strip()  # e.g., https://<site>.atlassian.net/wiki
CONFLUENCE_USERNAME = (os.environ.get("CONFLUENCE_USERNAME") or "").strip()
CONFLUENCE_URL = (os.environ.get("CONFLUENCE_URL") or "").strip()
JIRA_URL = (os.environ.get("JIRA_URL") or "").strip()
JIRA_USERNAME = (os.environ.get("JIRA_USERNAME") or "").strip()
JIRA_API_TOKEN = (os.environ.get("JIRA_API_TOKEN") or "").strip()
NAMESPACE = os.environ.get("PINECONE_NAMESPACE", "")
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME")
EMBED_DIM = 3072  # text-embedding-3-large 
REGION = os.environ.get("PINECONE_ENVIRONMENT")

print(MCP_COMMAND, MCP_ARGS,)
print("JIRA_URL : ", JIRA_URL,"JIRA_USERNAME :", JIRA_USERNAME )


async def startup():
    global mcp
    mcp = MCPServerStdio(
        params={
            "command": MCP_COMMAND,
            "args": MCP_ARGS,
            "env": {
                "JIRA_URL": JIRA_URL,
                "JIRA_USERNAME": JIRA_USERNAME,
                "JIRA_API_TOKEN": JIRA_API_TOKEN, 
            },
        },
        client_session_timeout_seconds=100,
    )
    await mcp.__aenter__()
    print(mcp.list_tools)

 
async def shutdown():
    global mcp
    if mcp:
        await mcp.__aexit__(None, None, None)
        print("🛑 MCP stdio stopped.")

def _normalize(text: str) -> str:
    """
    Normalize text for comparison:
    - lowercase
    - remove punctuation
    - collapse spaces
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokenize(text: str) -> set:
    """Split normalized text into tokens."""
    return set(_normalize(text).split())


def matches_label(
    input_text: str,
    labels: List[str],
    fuzzy_threshold: int = 70
) -> bool:
    """
    Check if input_text matches ANY label in labels list.
    Uses both token overlap and fuzzy similarity matching.

    Args:
        input_text: User input text to match
        labels: List of labels to match against
        fuzzy_threshold: Similarity threshold (0-100)

    Returns:
        True if match found, False otherwise
    """
    if not input_text or not labels:
        return False

    input_norm = _normalize(input_text)
    input_tokens = _tokenize(input_norm)

    for label in labels:
        label_norm = _normalize(label.replace("-", " "))
        label_tokens = _tokenize(label_norm)

        # Token overlap check
        if input_tokens & label_tokens:
            return True

        # Fuzzy similarity check
        score = fuzz.partial_ratio(input_norm, label_norm)
        if score >= fuzzy_threshold:
            return True

    return False


async def filter_jira(label: str): 
    await startup()
    jql = 'issuetype = Story ORDER BY updated DESC'
    TOOL_NAME = "jira_search"
    fields_csv = "key,summary,status,assignee,priority,created,updated,reporter,project,issuetype,labels,description"
    payload = {
        "jql": jql,
        "fields": fields_csv,  # CSV string per tool schema
        "limit": 200, # max issues to return
    }

    result = await mcp.call_tool(TOOL_NAME, payload)
    print("RAW TOOL RESULT:", result)
    print("structuredContent:", result.structuredContent)
    print("content:", result.content)
    print("error:", getattr(result, "error", None))

    # data = _mcp_result_to_dict(result) 
    data = json.loads(result.structuredContent["result"])
    issues = data.get("issues", [])
    print(f"Fetched {len(issues)} issues from Jira")
    # print("Sample Issue:", issues[0] if issues else "No issues found") 
    filtered_rows = []
    for issue in issues:
        labels = issue.get("labels", [])
        print(type(issue.get("labels")))
    # 🔍 label similarity check
        if matches_label(label, labels):
            row = {
                "Key": issue.get("key"),
                "Summary": issue.get("summary"),
                "Status": issue.get("status", {}).get("name"),
                "Assignee": issue.get("assignee", {}).get("displayName"),
                "Priority": issue.get("priority", {}).get("name"),
                "Project": issue.get("project", {}).get("key"),
                "description": issue.get("description"),
                "IssueType": issue.get("issuetype", {}).get("name"),
                "Labels":  labels,
                "Created": issue.get("created"),
                "Updated": issue.get("updated"),
            }
            filtered_rows.append(row)

    print(f"Matched {len(filtered_rows)} issues after label filtering")

    return filtered_rows
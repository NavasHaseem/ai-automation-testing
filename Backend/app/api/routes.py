from fastapi import APIRouter, HTTPException
from typing import List
from app.api.schemas import GenerateTestCasesRequest, GenerateTestCasesResponse

from tools.jira_fetch_tool import filter_jira
from Models.langgraph_model import build_context_agent_graph
from states.base_state import AgentState, JiraStory
from utils import write_testcases_csv

router = APIRouter()

@router.post(
    "/generate-testcases",
    response_model=GenerateTestCasesResponse
)
async def generate_testcases(request: GenerateTestCasesRequest):
    """
    Generate test cases for Jira stories filtered by label.
    """

    # 1️⃣ Fetch Jira stories
    jira_issues = await filter_jira(label=request.label)

    if not jira_issues:
        raise HTTPException(
            status_code=404,
            detail="No Jira stories found for the given label"
        )

    jira_issues = jira_issues[: request.limit]

    # 2️⃣ Build graph ONCE
    graph = build_context_agent_graph()

    results = []

    # 3️⃣ Process each Jira story
    for issue in jira_issues:
        jira_story = JiraStory(
            key=issue.get('Key'),
            labels= issue.get("Labels"),
            description=issue.get("description"),
            priority= issue.get("Priority"))
        

        state = AgentState(jira_story=jira_story)

        # 4️⃣ Run LangGraph
        final_state = graph.invoke(state)

        testcases = final_state["test_cases"]

        # 5️⃣ Persist output
        output_path = write_testcases_csv(
            jira_key=jira_story.key,
            testcases=testcases,
        )

        results.append(
            {
                "jira_key": jira_story.key,
                "testcases_count": len(testcases),
                "output_file": output_path,
            }
        )

    return {
        "success": True,
        "results": results,
    }

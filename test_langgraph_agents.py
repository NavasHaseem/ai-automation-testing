from Backend.Models.langgraph_model import build_context_agent_graph
from Backend.states.base_state import AgentState, JiraStory
import json
import pandas as pd
from tqdm import tqdm
from Backend.tools.jira_fetch_tool import filter_jira
import asyncio
from pathlib import Path

def test_context_agent():
    # -----------------------------
    # 1. Create sample Jira story
    # -----------------------------
    PROJECT_ROOT = Path(__file__).resolve().parents[0]  # adjust if needed
    
    path_dir = (
        PROJECT_ROOT
        / "data"
        / "json_files"
    )

    filename = "jira_stories.json"
    file_path = path_dir/filename

    # items  = asyncio.run(filter_jira(label="airline"))
    # with open( file_path, "w", encoding="utf-8") as f:
    #     json.dump(items, f, indent=2, ensure_ascii=False)
    with open(file_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    for item in tqdm(items):
        print(item.get('Key'),
              type(item.get("Labels")),
              item.get("Labels"))

        jira_story = JiraStory(
            key= item.get('Key'),
            labels=item.get("Labels"),
            description= item.get("description"),
            priority= item.get("Priority"))


        # -----------------------------
        # 2. Initialize state
        # -----------------------------
        initial_state = AgentState(
            jira_story=jira_story
        )

        # -----------------------------
        # 3. Build and run graph
        # -----------------------------
        graph = build_context_agent_graph()

        final_state = graph.invoke(initial_state)

        # structured_context = final_state["structured_context"]
        test_cases = final_state["test_cases"]
        # -----------------------------
        # 4. Inspect output
        # -----------------------------
        # print(type(final_state))
        print(final_state.keys())
        df = pd.DataFrame(
            [tc.model_dump() for tc in test_cases]
        ) 
        output_dir = (
        PROJECT_ROOT
        / "data"
        / "test_data"
        /"testcases_generated")
        file_name = f"{item.get('Key')}_test_cases.csv"
        path = output_dir/file_name
        df.to_csv(path, index=False)

if __name__ == "__main__":
    test_context_agent()

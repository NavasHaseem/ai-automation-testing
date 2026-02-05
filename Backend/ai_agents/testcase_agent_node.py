import json
from typing import Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from Backend.states.base_state import AgentState
from Backend.states.test_case_state import TestCaseList
from Backend.prompts.testcase_generate_prompt import TESTCASE_GENERATOR_PROMPT



def testcase_generator_node(AgentState: AgentState) -> Dict[str, Any]:
    """
    Agent 3: Test Case Generator

    Consumes:
      - StructuredContext (authoritative)
      - Jira story metadata (non-authoritative)

    Produces:
      - List[TestCaseRow]
    """

    # 1️⃣ Guardrail: structured context must exist
    if not AgentState.structured_context:
        AgentState.errors.append(
            "Structured context missing. Cannot generate test cases."
        )
        return {"test_cases": []}

    # 2️⃣ Serialize structured context for the prompt
    structured_context_json = json.dumps(
        AgentState.structured_context.model_dump(),
        indent=2,
    )

    # 3️⃣ Build prompt (STRICT input binding)
# - Key: {jira_story_key}
# - Labels: {jira_story_labels}
# - Fix Version: {jira_story_fix_version}
# - Priority: {jira_story_priority}

# 3. Jira Story Description (for naming only, not inference)
# {jira_story_description}


    prompt = TESTCASE_GENERATOR_PROMPT.format(
        jira_story_key=AgentState.jira_story.key,
        jira_story_priority = AgentState.jira_story.priority,
        jira_story_labels=", ".join(AgentState.jira_story.labels),
        jira_story_description = AgentState.jira_story.description,
        structured_context = structured_context_json,
    )

    # 4️⃣ LLM with strict structured output
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
    ).with_structured_output(TestCaseList)

    # 5️⃣ Invoke model
    results: TestCaseList = llm.invoke(
        [
            SystemMessage(
                content="You are a senior QA automation engineer."
            ),
            HumanMessage(content=prompt),
        ]
    )

    # 6️⃣ Persist on state
    AgentState.test_cases = results.test_cases

    # 7️⃣ Return state update for LangGraph
    return {"test_cases": results.test_cases}

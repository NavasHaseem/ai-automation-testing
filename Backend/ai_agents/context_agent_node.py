import json
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
# from langchain_anthropic import ChatAnthropic

# from langchain_community.llms import LlamaCpp
# from langchain.schema import SystemMessage, HumanMessage

from prompts.context_prompt import REASONING_PROMPT_V2
import json

from states.base_state import AgentState
from states.structured_context import StructuredContext

# -----------------------------
# LLM initialization
# -----------------------------
llm = ChatOpenAI(
    model="gpt-4o-mini",
).with_structured_output(StructuredContext) 

print("llm loaded")

def context_reasoning_node(AgentState: AgentState) -> Dict[str, Any]:
    """
    Context Agent reasoning node.
    Builds StructuredContext using Jira story + retrieved Pinecone chunks.
    """

    # -----------------------------
    # Guard: ensure retrieval exists
    # -----------------------------
    if not AgentState.retrieved_chunks:
        AgentState.errors.append("No retrieved chunks available for context reasoning.")
        return {"structured_context": None}

    # -----------------------------
    # Prepare chunks JSON
    # -----------------------------
    retrieved_chunks_json = json.dumps(
        [
            {
                "chunk_id": c.chunk_id,
                "text": c.text,
                "source": c.source,
                "namespace": c.namespace,
                "metadata": c.metadata,
            }
            for c in AgentState.retrieved_chunks
        ],
        indent=2,
    )

    # -----------------------------
    # Build final prompt
    # -----------------------------
    prompt = REASONING_PROMPT_V2.format(
        jira_labels=", ".join(AgentState.jira_story.labels),
        jira_description=AgentState.jira_story.description,
        jira_summary = AgentState.jira_story.summary,
        retrieved_chunks_json=retrieved_chunks_json)
    
    # -----------------------------
    # Invoke LLM
    # -----------------------------
    structured_context: StructuredContext = llm.invoke(
        [
            SystemMessage(content="You are a Context Builder Agent."),
            HumanMessage(content=prompt),
        ]
    )
    
    # -----------------------------
    # Update state
    # -----------------------------
    AgentState.structured_context = structured_context

    return {"structured_context": structured_context}

from typing import List, Dict, Literal
from pydantic import BaseModel, Field
from enum import Enum

# -----------------------------
# Evidence Reference
# -----------------------------

class EvidenceRef(BaseModel):
    chunk_id: str = Field(..., description="ID of the Pinecone chunk supporting this statement")
    source: str = Field(..., description="Source system of the chunk (jira, confluence, mongodb, logs)")
    namespace: str = Field(..., description="Pinecone namespace where the chunk resides")


# -----------------------------
# Intent Identification
# -----------------------------

class IntentIdentification(BaseModel):
    summary: str = Field(
        ...,
        description="High-level reason why this Jira story exists, inferred from acceptance criteria"
    )
    evidence: List[EvidenceRef] = Field(
        default_factory=list,
        description="Chunks that support this intent"
    )


# -----------------------------
# Story Goal
# -----------------------------

class StoryGoal(BaseModel):
    goal_statement: str = Field(
        ...,
        description="Concrete outcome that must be achieved to satisfy acceptance criteria"
    )
    success_conditions: List[str] = Field(
        default_factory=list,
        description="Explicit success conditions derived from acceptance criteria"
    )
    evidence: List[EvidenceRef] = Field(
        default_factory=list,
        description="Chunks that justify or clarify the goal"
    )

# -----------------------------
#  Structural Behaviour 
# -----------------------------

class BehaviorIntent(str, Enum):
    FUNCTIONAL = "Functional"
    VALIDATION = "Validation"
    NEGATIVE = "Negative"
    BOUNDARY = "Boundary"
    INTEGRATION = "Integration"
    SECURITY = "Security"


class Evidence(BaseModel):
    chunk_id: str
    source: str
    namespace: str

class TestableBehavior(BaseModel):
    behavior_id: str = Field(
        ...,
        description="Unique identifier for the behavior within the Jira story"
    )
    behavior_description: str = Field(
        ...,
        description="Clear description of the promised system behavior"
    )
    behavior_intent: BehaviorIntent = Field(
        ...,
        description="Testing intent classification for this behavior"
    )
    derived_from: str = Field(
        ...,
        description="Reference to acceptance criteria, rule, or story section"
    )
    observable_outcome: str = Field(
        ...,
        description="Externally observable result used to verify behavior"
    )
    evidence: List[Evidence] = Field(
        default_factory=list,
        description="Supporting evidence from retrieved chunks or AC"
    )


# -----------------------------
# In-Scope Systems
# -----------------------------

class InScopeSystem(BaseModel):
    system_name: str = Field(
        ...,
        description="Name of the system/component involved"
    )
    system_type: Literal["API", "Service", "Database", "External", "Other"] = Field(
        ...,
        description="Type of system based on retrieved evidence"
    )
    responsibility: str = Field(
        ...,
        description="What role this system plays in the story"
    )
    evidence: List[EvidenceRef] = Field(
        default_factory=list,
        description="Chunks that indicate this system is in scope"
    )


# -----------------------------
# Constraints & Rules
# -----------------------------

class ConstraintRule(BaseModel):
    rule: str = Field(
        ...,
        description="Constraint, validation, or rule that must hold true"
    )
    rule_type: Literal["Functional", "Validation", "Performance", "Security", "Operational"] = Field(
        ...,
        description="Nature of the rule"
    )
    derived_from: Literal["AcceptanceCriteria", "RetrievedChunk"] = Field(
        ...,
        description="Origin of the rule"
    )
    evidence: List[EvidenceRef] = Field(
        default_factory=list,
        description="Chunks or AC references that support this rule"
    )


# -----------------------------
# Final Structured Context
# -----------------------------

class StructuredContext(BaseModel):
    story_intent: IntentIdentification
    story_goal: StoryGoal
    in_scope_systems: List[InScopeSystem] = Field(default_factory=list)
    testable_behaviors: List[TestableBehavior] = Field(default_factory=list)
    constraints_and_rules: List[ConstraintRule] = Field(default_factory=list)

    grounding_statement: str = Field(
        ...,
        description=(
            "Explicit declaration that all information is derived only from "
            "Jira description/acceptance criteria and retrieved Pinecone chunks"
        )
    )



class GenerateContextResponse(BaseModel):
    jira_key: str
    structured_context: StructuredContext

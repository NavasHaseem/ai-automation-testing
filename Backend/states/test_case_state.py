from typing import Literal, List
from pydantic import BaseModel, Field


from enum import Enum

class BehaviorIntent(str, Enum):
    FUNCTIONAL = "Functional"
    VALIDATION = "Validation"
    NEGATIVE = "Negative"
    BOUNDARY = "Boundary"
    INTEGRATION = "Integration"
    SECURITY = "Security"
<<<<<<< HEAD
=======
    #smoke
    #sanity
    #regression
>>>>>>> feature


class TestCaseRow(BaseModel):
    """
    Represents a single, independent test case row.
    This schema maps 1:1 with the final CSV output.
    """

    external_id: str = Field(
        description="Unique test case identifier, numeric or alphanumeric."
    )

    name: str = Field(
        description="Short, clear test case name describing the validation."
    )

    scenario: str = Field(
        description=(
            "Scenario description such as positive, negative, boundary, "
            "or validation focus. Free text but must be explicit."
        )
    )

    label: str = Field(
        description=(
            "Classification label including layer and execution intent "
            "(e.g., UI_Validation, API_Regression, UI_Smoke)."
        )
    )

    test_type: BehaviorIntent = Field(
        description=(
            "Type of test case derived directly from behavior intent. "
            "Must be one of: Functional, Validation, Negative, Boundary, "
            "Integration, Security."
        )
    )


    fix_version: str = Field(
        description="Target sprint or release version (e.g., Sprint_2026_01)."
    )

    priority: Literal["High", "Medium", "Low"] = Field(
        description="Business priority of the test case."
    )

    test_steps: str = Field(
        description=(
            "Ordered, automation-friendly steps. "
            "Must be numbered and deterministic."
        )
    )

    expected_result: str = Field(
        description=(
            "Binary, verifiable outcome. "
            "Must clearly indicate pass/fail behavior."
        )
    )

    test_data: str = Field(
        description=(
            "Concrete test data used in execution. "
            "If not required, must explicitly say 'Test data not needed'."
        )
    )

class TestCaseList(BaseModel):
    """
    Wrapper required for LangChain structured output.
    """
    test_cases: List[TestCaseRow]

class GenerateTestCasesResponse(BaseModel):
    jira_key: str = Field(..., example="AATA-12")
    testcases: List[TestCaseRow]


 
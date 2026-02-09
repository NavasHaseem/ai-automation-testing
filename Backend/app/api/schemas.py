from pydantic import BaseModel
from typing import Optional, List

class GenerateTestCasesRequest(BaseModel):
    label: str
    limit: Optional[int] = 1   # number of Jira stories

class GeneratedTestCaseResponse(BaseModel):
    jira_key: str
    testcases_count: int
    output_file: str

class GenerateTestCasesResponse(BaseModel):
    success: bool
    results: List[GeneratedTestCaseResponse]

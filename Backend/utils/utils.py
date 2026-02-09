import pandas as pd
from typing import List
from states.test_case_state import TestCaseRow

def write_testcases_csv(
    jira_key: str,
    testcases: List[TestCaseRow],
    output_dir="output"
) -> str:
    df = pd.DataFrame([tc.model_dump() for tc in testcases])
    path = f"{output_dir}/{jira_key}_testcases.csv"
    df.to_csv(path, index=False)
    return path


# jira_api.py
import os
import requests
from typing import Dict, Any, List

BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_TOKEN = os.getenv("JIRA_API_TOKEN")

AUTH = (JIRA_EMAIL, JIRA_TOKEN)
HEADERS = {"Accept": "application/json"}

def get_issue(key: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/rest/api/3/issue/{key}"
    r = requests.get(url, headers=HEADERS, auth=AUTH)
    r.raise_for_status()
    return r.json()

def search_jql(jql: str, fields: List[str] | None = None, max_results: int = 50) -> Dict[str, Any]:
    # New endpoint for JQL search
    url = f"{BASE_URL}/rest/api/3/search/jql"
    params = {"jql": jql, "maxResults": max_results}
    if fields:
        params["fields"] = ",".join(fields)
    r = requests.get(url, headers=HEADERS, auth=AUTH, params=params)
    r.raise_for_status()
    return r.json()

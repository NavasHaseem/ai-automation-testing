
# utils/jira_filter.py
from typing import Dict, Any, List

def build_pinecone_filter_from_issue(
    jira_project: str | None,
    jira_labels: List[str] | None,
    jira_components: List[str] | None,
    restrict_to_source: str = "mongodb",
    strategy: str = "project_and_any_label_or_component",
) -> Dict[str, Any]:

    clauses: List[Dict[str, Any]] = []

    # Always filter by source if provided
    if restrict_to_source:
        clauses.append({"source": {"$eq": restrict_to_source}})

    if jira_project:
        clauses.append({"jira_project": {"$eq": jira_project}})

    labels_clause = None
    comps_clause = None

    if jira_labels:
        labels_clause = {"jira_labels": {"$in": jira_labels}}

    if jira_components:
        comps_clause = {"jira_components": {"$in": jira_components}}

    if strategy == "project_and_any_label_or_component":

        sub_or = []
        if labels_clause:
            sub_or.append(labels_clause)
        if comps_clause:
            sub_or.append(comps_clause)

        if sub_or:
            return {"$and": clauses + [{"$or": sub_or}]}
        else:

            return {"$and": clauses} if len(clauses) > 1 else (clauses[0] if clauses else {})

    elif strategy == "project_and_labels_only":
        if labels_clause:
            return {"$and": clauses + [labels_clause]}
        return {"$and": clauses} if len(clauses) > 1 else (clauses[0] if clauses else {})

    elif strategy == "labels_or_components_only":
        sub_or = []
        if labels_clause:
            sub_or.append(labels_clause)
        if comps_clause:
            sub_or.append(comps_clause)
        return {"$or": sub_or} if sub_or else {}


    return {"$and": clauses} if len(clauses) > 1 else (clauses[0] if clauses else {})

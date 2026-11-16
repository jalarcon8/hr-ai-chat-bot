"""In-memory MCP observations for controlled synthetic F004 acceptance scenarios."""

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from unittest.mock import patch


@dataclass(repr=False)
class ObservedCall:
    name: str
    arguments: dict = field(repr=False)
    result: dict | None = field(repr=False)
    is_error: bool


@contextmanager
def observe_calls(mcp):
    observations = []
    original_call = mcp.call

    async def observe(name, arguments):
        observation = ObservedCall(name, deepcopy(arguments), None, True)
        observations.append(observation)
        result = await original_call(name, arguments)
        observation.result = deepcopy(result.structuredContent)
        observation.is_error = result.isError
        return result

    with patch.object(mcp, "call", side_effect=observe):
        yield observations


def require(condition, classification):
    if not condition:
        raise AssertionError(classification)


def policy_citation_matches(response, observations, document_id):
    for call in observations:
        if call.name != "search_policy_documents" or call.is_error:
            continue
        if not isinstance(call.result, dict):
            continue
        evidence = call.result.get("evidence", [])
        if not isinstance(evidence, list):
            continue
        for item in evidence:
            if not isinstance(item, dict) or item.get("document_id") != document_id:
                continue
            for citation in response.citations:
                if (
                    citation.source_type == "policy_evidence"
                    and citation.document_id == document_id
                    and citation.title == item.get("title")
                    and citation.section == item.get("section")
                    and citation.snippet == item.get("snippet")
                    and citation.chunk_id == item.get("chunk_id")
                    and bool(citation.snippet)
                ):
                    return True
    return False

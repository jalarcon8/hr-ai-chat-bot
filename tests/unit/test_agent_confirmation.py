import asyncio
import hashlib
import json
from copy import deepcopy

import pytest

from hr_agent.agent import HRAgent
from hr_agent.config import AgentConfig
from tests.unit.agent_orchestration_helpers import (
    FakeMCPClient,
    ScriptedLLM,
    tool_completion,
)


def test_draft_confirmation_is_bound_to_exact_proposal_and_does_not_send():
    arguments = {"recipient_name": "Example", "purpose": "Synthetic request"}
    llm = ScriptedLLM([tool_completion("draft_hr_email", arguments, "draft-1")])
    mcp = FakeMCPClient(
        results={
            "draft_hr_email": {
                "status": "found",
                "draft": {"subject": "Synthetic request", "body": "Example draft body"},
            }
        }
    )

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        response = await agent.process_request("Draft a synthetic HR email.")
        assert response.status == "confirmation_required"
        assert response.confirmation_required
        assert response.action_id and response.pending_action
        assert "Example draft body" in response.confirmation_prompt
        assert "No email was sent" in response.answer
        assert len(mcp.calls) == 1
        changed = deepcopy(response.pending_action)
        changed["draft"]["body"] = "Changed body"
        with pytest.raises(ValueError, match="does not match"):
            await agent.confirm_action(response.action_id, True, {"pending_action": changed})
        forged = deepcopy(changed)
        proposal = {key: value for key, value in forged.items() if key != "action_id"}
        forged["action_id"] = hashlib.sha256(
            json.dumps(proposal, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        with pytest.raises(ValueError, match="does not match"):
            await agent.confirm_action(forged["action_id"], True, {"pending_action": forged})
        with pytest.raises(ValueError):
            await agent.confirm_action("wrong", True, {"pending_action": response.pending_action})
        with pytest.raises(ValueError):
            await agent.confirm_action(response.action_id, "yes", {"pending_action": response.pending_action})
        confirmed = await agent.confirm_action(
            response.action_id, True, {"pending_action": response.pending_action}
        )
        cancelled = await agent.confirm_action(
            response.action_id, False, {"pending_action": response.pending_action}
        )
        assert confirmed.status == "answered" and "No email was sent" in confirmed.answer
        assert "cancelled" in cancelled.answer and "No email was sent" in cancelled.answer
        assert len(mcp.calls) == 1

    asyncio.run(exercise())


def test_new_identical_proposals_require_separate_confirmation():
    arguments = {"recipient_name": "Example", "purpose": "Synthetic request"}
    llm = ScriptedLLM(
        [tool_completion("draft_hr_email", arguments, "one"),
         tool_completion("draft_hr_email", arguments, "two")]
    )
    mcp = FakeMCPClient(
        results={"draft_hr_email": {"status": "found", "draft": {"subject": "s", "body": "b"}}}
    )

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        first = await agent.process_request("Draft an email.")
        second = await agent.process_request("Draft another email.")
        assert first.action_id != second.action_id
        with pytest.raises(ValueError):
            await agent.confirm_action(first.action_id, True, {"pending_action": second.pending_action})

    asyncio.run(exercise())

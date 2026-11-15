import asyncio
import os
from types import SimpleNamespace

import pytest

from hr_agent.config import AgentConfig, get_agent_setting
from hr_agent.llm import GroqLLMClient
from tests.integration.test_agent_provider import (
    test_configured_provider_model_supports_tool_calling as run_provider_smoke,
)


def test_dotenv_supplies_settings_without_changing_process_environment(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for name in ("AGENT_MODEL_NAME", "GROQ_MODEL", "AGENT_MAX_TOKENS", "GROQ_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    (tmp_path / ".env").write_text(
        "AGENT_MODEL_NAME=local-model\nAGENT_MAX_TOKENS=256\nGROQ_API_KEY=local-test-key\n",
        encoding="utf-8",
    )

    config = AgentConfig.from_environment()
    assert config.model_name == "local-model"
    assert config.max_tokens == 256
    assert get_agent_setting("GROQ_API_KEY") == "local-test-key"
    assert "GROQ_API_KEY" not in os.environ


def test_process_variables_override_dotenv_including_model_alias(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AGENT_MODEL_NAME", raising=False)
    monkeypatch.setenv("GROQ_MODEL", "process-model")
    monkeypatch.setenv("GROQ_API_KEY", "process-test-key")
    (tmp_path / ".env").write_text(
        "AGENT_MODEL_NAME=local-model\nGROQ_API_KEY=local-test-key\n", encoding="utf-8"
    )

    assert AgentConfig.from_environment().model_name == "process-model"
    assert get_agent_setting("GROQ_API_KEY") == "process-test-key"
    monkeypatch.setenv("AGENT_MODEL_NAME", "agent-model")
    assert AgentConfig.from_environment().model_name == "agent-model"


def test_llm_client_uses_dotenv_key_without_mutating_environment(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    (tmp_path / ".env").write_text("GROQ_API_KEY=local-test-key\n", encoding="utf-8")
    received_keys = []

    class FakeCompletions:
        async def create(self, **kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok", tool_calls=None))]
            )

    class FakeGroq:
        def __init__(self, *, api_key):
            received_keys.append(api_key)
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("hr_agent.llm.AsyncGroq", FakeGroq)
    response = asyncio.run(GroqLLMClient().complete([], [], config=AgentConfig()))
    assert response.content == "ok"
    assert received_keys == ["local-test-key"]
    assert "GROQ_API_KEY" not in os.environ


def test_live_provider_is_disabled_by_default_even_with_dotenv_key(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AGENT_RUN_PROVIDER_SMOKE", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    (tmp_path / ".env").write_text("GROQ_API_KEY=local-test-key\n", encoding="utf-8")

    with pytest.raises(pytest.skip.Exception):
        run_provider_smoke(tmp_path)


def test_process_flag_disables_dotenv_live_opt_in(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENT_RUN_PROVIDER_SMOKE", "0")
    (tmp_path / ".env").write_text(
        "AGENT_RUN_PROVIDER_SMOKE=1\nGROQ_API_KEY=local-test-key\n", encoding="utf-8"
    )

    with pytest.raises(pytest.skip.Exception):
        run_provider_smoke(tmp_path)

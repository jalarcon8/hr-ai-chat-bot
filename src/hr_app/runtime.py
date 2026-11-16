"""Session-scoped synchronous bridge to the asynchronous HR agent."""

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future
from typing import Any

from hr_agent.agent import HRAgent
from hr_agent.config import AgentConfig
from hr_agent.llm import GroqLLMClient
from hr_agent.types import AgentResponse
from hr_mcp.client import ClientError, MCPClient


async def _discover_mcp_tools(config: AgentConfig) -> int:
    async with MCPClient(
        command=config.mcp_server_command,
        args=list(config.mcp_server_args),
    ) as mcp_client:
        return len(await mcp_client.discover())


def health_status(
    *,
    probe: bool = True,
    config: AgentConfig | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "app": {"status": "healthy"},
        "mcp": {"status": "unchecked", "tool_count": None, "error_code": None},
    }
    if not probe:
        return result

    try:
        selected_config = config or AgentConfig.from_environment()
        tool_count = asyncio.run(_discover_mcp_tools(selected_config))
    except ValueError:
        result["mcp"] = {
            "status": "failed",
            "tool_count": None,
            "error_code": "invalid_configuration",
        }
    except ClientError as exc:
        result["mcp"] = {
            "status": "failed",
            "tool_count": None,
            "error_code": exc.code,
        }
    else:
        result["mcp"] = {
            "status": "healthy",
            "tool_count": tool_count,
            "error_code": None,
        }
    return result


class AgentSession:
    """Keep one agent and MCP session on a private event loop for one UI session."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        self._config = config or AgentConfig.from_environment()
        self._lock = threading.RLock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._agent: HRAgent | None = None
        self._shutdown: asyncio.Event | None = None
        self._ready: Future[None] | None = None
        self._lifecycle: Future[None] | None = None

    def process_request(
        self,
        user_input: str,
        context: dict[str, object] | None = None,
    ) -> AgentResponse:
        with self._lock:
            self._ensure_started()
            assert self._agent is not None
            return self._submit(self._agent.process_request(user_input, context=context))

    def confirm_action(
        self,
        action_id: str,
        confirmation: bool,
        context: dict[str, object],
    ) -> AgentResponse:
        with self._lock:
            self._ensure_started()
            assert self._agent is not None
            return self._submit(
                self._agent.confirm_action(action_id, confirmation, context)
            )

    def close(self) -> None:
        with self._lock:
            loop = self._loop
            thread = self._thread
            if loop is None or thread is None:
                return

            if self._shutdown is not None and self._lifecycle is not None:
                loop.call_soon_threadsafe(self._shutdown.set)
                self._lifecycle.result()
            if loop.is_running():
                loop.call_soon_threadsafe(loop.stop)
            thread.join()
            self._reset()

    def _ensure_started(self) -> None:
        if self._loop is not None:
            return

        loop = asyncio.new_event_loop()
        ready: Future[None] = Future()
        thread = threading.Thread(
            target=self._serve,
            args=(loop, ready),
            name="hr-agent-session",
            daemon=True,
        )
        self._loop = loop
        self._thread = thread
        self._ready = ready
        thread.start()

        try:
            ready.result()
        except Exception:
            if loop.is_running():
                loop.call_soon_threadsafe(loop.stop)
            thread.join()
            self._reset()
            raise

    def _serve(self, loop: asyncio.AbstractEventLoop, ready: Future[None]) -> None:
        asyncio.set_event_loop(loop)
        lifecycle = asyncio.run_coroutine_threadsafe(
            self._run_agent_session(ready),
            loop,
        )
        self._lifecycle = lifecycle

        def stop_after_failure(future: Future[None]) -> None:
            if future.cancelled():
                return
            exception = future.exception()
            if exception is not None and loop.is_running():
                loop.call_soon_threadsafe(loop.stop)

        lifecycle.add_done_callback(stop_after_failure)
        loop.run_forever()
        loop.close()

    async def _run_agent_session(self, ready: Future[None]) -> None:
        try:
            async with MCPClient(
                command=self._config.mcp_server_command,
                args=list(self._config.mcp_server_args),
            ) as mcp_client:
                self._agent = await HRAgent.create(
                    mcp_client,
                    GroqLLMClient(),
                    self._config,
                )
                self._shutdown = asyncio.Event()
                ready.set_result(None)
                await self._shutdown.wait()
        except Exception as exc:
            if not ready.done():
                ready.set_exception(exc)
            raise

    def _submit(self, operation: Any) -> AgentResponse:
        if self._loop is None:
            raise RuntimeError("The agent session is not running.")
        return asyncio.run_coroutine_threadsafe(operation, self._loop).result()

    def _reset(self) -> None:
        self._loop = None
        self._thread = None
        self._agent = None
        self._shutdown = None
        self._ready = None
        self._lifecycle = None

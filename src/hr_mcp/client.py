"""Developer-facing client for an MCP server over stdio."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from datetime import timedelta
from types import TracebackType
from typing import Any, Literal, Self

from anyio import BrokenResourceError, ClosedResourceError, EndOfStream
from mcp import ClientSession, McpError, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, TextContent, Tool
from pydantic import ValidationError

from .models import ErrorEnvelope, TraceEvent, UnclassifiedError
from .trace import TracePersistenceError, TraceSink, sanitize_sdk_logging

EXAMPLES: dict[str, dict[str, Any]] = {
    "search_policy_documents": {"question": "What approval is required before out-of-state travel?"},
    "get_policy_section": {"document_id": "HR-004", "section": "2.2 Working from another state"},
    "lookup_employee_profile": {"employee_id": "SYN-001"},
    "check_pto_balance": {"employee_id": "SYN-001"},
    "check_policy_compliance": {"check_id": "out_of_state_prior_approval"},
    "draft_hr_email": {"recipient_name": "Alex Example", "purpose": "PTO request"},
}
_TRANSPORT_ERRORS = (OSError, EOFError, BrokenResourceError, ClosedResourceError, EndOfStream)
_SERVER_ENVIRONMENT = (
    "HR_RAG_CORPUS_DIR",
    "HR_RAG_INDEX_DIR",
    "HR_RAG_EMBEDDING_MODEL",
    "HR_RAG_EMBEDDING_REVISION",
    "HR_RAG_TOKENIZER_ID",
    "HR_RAG_CHUNK_TOKENS",
    "HR_RAG_CHUNK_OVERLAP",
    "HR_RAG_TOP_K",
)


class ClientError(Exception):
    """A locally established MCP client failure."""

    def __init__(
        self,
        code: str,
        *,
        classification: str | None = None,
        origin: str | None = None,
        protocol_code: int | None = None,
    ) -> None:
        self.code = code
        self.classification = classification
        self.origin = origin
        self.protocol_code = protocol_code
        super().__init__(code)


class MCPClient:
    def __init__(
        self,
        *,
        command: str | None = None,
        args: list[str] | None = None,
        call_timeout: timedelta = timedelta(minutes=5),
        trace_sink: TraceSink | None = None,
    ) -> None:
        sanitize_sdk_logging()
        self._command = command or sys.executable
        self._args = args if args is not None else ["-m", "hr_mcp.server"]
        self._call_timeout = call_timeout
        self._trace_sink = trace_sink if trace_sink is not None else TraceSink.from_environment()
        self._stack = AsyncExitStack()
        self._session: ClientSession | None = None

    def _trace(
        self,
        event_type: Literal["discovery", "tool_call"],
        outcome: str,
        *,
        tool: str | None = None,
        classification: Literal[
            "INVALID_ARGUMENT", "OPERATIONAL_ERROR", "UNKNOWN_ERROR", "UNCLASSIFIED_ERROR"
        ] | None = None,
    ) -> None:
        try:
            self._trace_sink.write(
                TraceEvent(
                    component="client",
                    event_type=event_type,
                    tool=tool,
                    outcome=outcome,
                    classification=classification,
                )
            )
        except TracePersistenceError:
            raise ClientError(
                "trace_persistence_failure",
                classification="OPERATIONAL_ERROR",
                origin="trace_persistence",
            ) from None

    async def __aenter__(self) -> Self:
        try:
            env = {key: os.environ[key] for key in _SERVER_ENVIRONMENT if key in os.environ}
            env["HR_MCP_TRACE_PATH"] = str(self._trace_sink.path)
            read, write = await self._stack.enter_async_context(
                stdio_client(
                    StdioServerParameters(
                        command=self._command,
                        args=self._args,
                        env=env,
                    )
                )
            )
            session = await self._stack.enter_async_context(
                ClientSession(read, write, read_timeout_seconds=timedelta(seconds=5))
            )
            await session.initialize()
        except _TRANSPORT_ERRORS:
            await self._stack.aclose()
            self._trace("discovery", "transport_failure")
            raise ClientError("transport_failure") from None
        except McpError as exc:
            await self._stack.aclose()
            self._trace("discovery", "UNCLASSIFIED_ERROR", classification="UNCLASSIFIED_ERROR")
            raise ClientError(
                "unclassified_error",
                classification="UNCLASSIFIED_ERROR",
                protocol_code=exc.error.code,
            ) from None
        self._session = session
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._session = None
        # Passing the caller's exception into AnyIO task groups wraps it in an ExceptionGroup.
        try:
            await self._stack.aclose()
        except ExceptionGroup as cleanup_error:
            if not isinstance(exc, ClientError):
                raise
            _, unexpected = cleanup_error.split(BrokenResourceError)
            if unexpected is not None:
                raise unexpected from exc

    def _connected_session(self) -> ClientSession:
        if self._session is None:
            raise ClientError("transport_failure")
        return self._session

    async def discover(self) -> list[Tool]:
        try:
            tools = (await self._connected_session().list_tools()).tools
        except (*_TRANSPORT_ERRORS, McpError):
            self._trace("discovery", "discovery_failure")
            raise ClientError("discovery_failure") from None
        except ClientError:
            self._trace("discovery", "transport_failure")
            raise
        self._trace("discovery", "found")
        return tools

    async def call(self, name: str, arguments: dict[str, Any]) -> CallToolResult:
        if name not in {tool.name for tool in await self.discover()}:
            self._trace("tool_call", "unknown_tool")
            raise ClientError("unknown_tool")
        trace_tool = name if name in EXAMPLES else None
        try:
            result = await self._connected_session().call_tool(
                name, arguments, read_timeout_seconds=self._call_timeout
            )
        except _TRANSPORT_ERRORS:
            self._trace("tool_call", "transport_failure", tool=trace_tool)
            raise ClientError("transport_failure") from None
        except McpError as exc:
            self._trace(
                "tool_call", "UNCLASSIFIED_ERROR", tool=trace_tool, classification="UNCLASSIFIED_ERROR"
            )
            raise ClientError(
                "unclassified_error",
                classification="UNCLASSIFIED_ERROR",
                protocol_code=exc.error.code,
            ) from None
        except (RuntimeError, ValidationError):
            self._trace(
                "tool_call", "UNCLASSIFIED_ERROR", tool=trace_tool, classification="UNCLASSIFIED_ERROR"
            )
            raise ClientError("unclassified_error", classification="UNCLASSIFIED_ERROR") from None
        if result.isError:
            try:
                details = ErrorEnvelope.model_validate(result.structuredContent)
                content = details.model_dump(mode="json")
            except ValidationError:
                content = {"error": UnclassifiedError().model_dump(mode="json")}
                self._trace(
                    "tool_call", "UNCLASSIFIED_ERROR", tool=trace_tool, classification="UNCLASSIFIED_ERROR"
                )
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text="Tool request failed.")],
                structuredContent=content,
            )
        return result


async def _run(args: argparse.Namespace) -> int:
    try:
        async with MCPClient() as client:
            if args.discover:
                tools = await client.discover()
                print(json.dumps([tool.model_dump(mode="json") for tool in tools], indent=2))
                return 0
            result = await client.call(args.example, EXAMPLES[args.example])
            print(json.dumps(result.model_dump(mode="json", exclude_none=True), indent=2))
            return 1 if result.isError else 0
    except ClientError as exc:
        if exc.classification is not None:
            print(
                json.dumps(
                    {"error": {"classification": exc.classification, "origin": exc.origin, "code": exc.code}}
                ),
                file=sys.stderr,
            )
        else:
            print(f"MCP client error: {exc.code}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover or call fictional HR MCP tools.")
    commands = parser.add_mutually_exclusive_group(required=True)
    commands.add_argument("--discover", action="store_true")
    commands.add_argument("--example", choices=sorted(EXAMPLES))
    return asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())

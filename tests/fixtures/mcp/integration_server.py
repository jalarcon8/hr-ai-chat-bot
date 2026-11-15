"""Test-only stdio server with real handlers and a synthetic compliance baseline."""

import argparse
import asyncio
import inspect
import json
import socket
import time
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

from mcp import McpError
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ErrorData,
    ListToolsRequest,
    TextContent,
)

from hr_mcp import policy, tools
from hr_mcp.data import SyntheticData
from hr_mcp.server import create_handlers, create_server
from hr_rag.config import Settings
from hr_rag.models import EmbeddingError
from tests.fixtures.mcp.doubles import DeterministicEmbedder

FIXTURES = Path(__file__).parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus", type=Path)
    parser.add_argument("index", type=Path)
    parser.add_argument("mode", nargs="?", default="normal")
    parser.add_argument("--baseline", type=Path, default=FIXTURES / "baseline.json")
    parser.add_argument("--pin", type=Path, default=FIXTURES / "baseline-pin.json")
    parser.add_argument("--data-dir", type=Path, default=FIXTURES)
    parser.add_argument("--marker", type=Path)
    args = parser.parse_args()
    corpus, index = args.corpus, args.index
    settings = Settings(corpus_dir=corpus, index_dir=index)

    class TestEmbedder(DeterministicEmbedder):
        def encode(self, texts):
            if texts == ["synthetic-embedding-failure"]:
                raise EmbeddingError("Synthetic secret must not appear in logs.")
            return super().encode(texts)

    handlers = create_handlers(
        settings,
        SyntheticData(args.data_dir / "employees.json", args.data_dir / "pto.json"),
        TestEmbedder,
    )
    retrieve = policy.retrieve

    def test_retrieve(question, *values, **kwargs):
        result = retrieve(question, *values, **kwargs)
        if question == "synthetic-empty-result":
            return replace(result, evidence=())
        return result

    policy.retrieve = test_retrieve
    draft = handlers["draft_hr_email"]

    def test_draft(arguments: dict[str, Any]) -> dict[str, Any]:
        if arguments["purpose"] == "synthetic-handler-failure":
            raise RuntimeError("Synthetic secret must not appear in logs.")
        if arguments["purpose"] == "synthetic-bad-output":
            return {"draft": {"subject": "Synthetic", "body": "Incomplete response"}}
        result = draft(arguments)
        assert isinstance(result, dict)
        return result

    handlers["draft_hr_email"] = test_draft
    if args.mode == "slow-search":
        search = handlers["search_policy_documents"]

        async def slow_search(arguments: dict[str, Any]) -> dict[str, Any]:
            await asyncio.sleep(6)
            result = search(arguments)
            if not isinstance(result, dict):
                return await result
            return result

        handlers["search_policy_documents"] = slow_search
    elif args.mode == "blocking-search":
        search = handlers["search_policy_documents"]

        def blocking_search(arguments):
            time.sleep(0.8)
            return search(arguments)

        handlers["search_policy_documents"] = blocking_search
    pin = json.loads(args.pin.read_text(encoding="utf-8"))

    def synthetic_compliance(arguments: dict[str, Any]) -> dict[str, Any]:
        return tools._check_policy_compliance(
            arguments["check_id"],
            arguments["approval_facts"],
            index_dir=index,
            corpus_dir=corpus,
            baseline_path=args.baseline,
            pin=pin,
        ).model_dump(mode="json")

    handlers["check_policy_compliance"] = synthetic_compliance

    if args.marker:
        def instrument(name, handler):
            async def wrapped(arguments):
                with args.marker.open("a", encoding="utf-8") as marker:
                    marker.write(name + "\n")
                result = handler(arguments)
                return await result if inspect.isawaitable(result) else result
            return wrapped

        handlers = {name: instrument(name, handler) for name, handler in handlers.items()}

    server = create_server(handlers)
    if args.mode == "adapter-error":
        registration = server._tool_manager.get_tool("draft_hr_email")
        assert registration is not None
        registration.parameters["type"] = "invalid-schema-type"
    elif args.mode == "ambiguous":
        @server._mcp_server.call_tool(validate_input=False)
        async def ambiguous(name, arguments):
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text="synthetic secret: " + arguments["purpose"])],
                structuredContent=(
                    None if arguments["purpose"] == "missing-envelope"
                    else {"error": {"classification": "made-up"}}
                ),
            )
    elif args.mode == "protocol-error":
        async def protocol_error(request):
            raise McpError(ErrorData(code=-32603, message="synthetic secret: INVALID_ARGUMENT"))

        server._mcp_server.request_handlers[CallToolRequest] = protocol_error
    elif args.mode == "discovery-error":
        async def discovery_error(request):
            raise McpError(ErrorData(code=-32603, message="synthetic secret"))

        server._mcp_server.request_handlers[ListToolsRequest] = discovery_error
    def loopback_only(method):
        def connect(sock, address):
            # Windows asyncio uses a loopback socket pair for its own wakeups.
            if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
                return method(sock, address)
            raise RuntimeError("External network access is disabled.")

        return connect

    with (
        patch("socket.socket.connect", loopback_only(socket.socket.connect)),
        patch("socket.socket.connect_ex", loopback_only(socket.socket.connect_ex)),
        patch("socket.create_connection", side_effect=RuntimeError("Network access is disabled.")),
    ):
        server.run(transport="stdio")


if __name__ == "__main__":
    main()

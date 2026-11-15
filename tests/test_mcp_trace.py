import asyncio
import json
import sys
from datetime import datetime
from uuid import UUID

import pytest
from mcp.client.stdio import get_default_environment

from hr_mcp.client import ClientError, MCPClient
from hr_mcp.trace import TracePersistenceError, TraceSink
from tests.fixtures.mcp.harness import build_context, call, connect
from tests.test_mcp_errors import assert_error


@pytest.fixture
def context(tmp_path):
    return build_context(tmp_path)


@pytest.mark.parametrize("kind", ["provided", "raw"])
def test_persisted_traces_are_allowlisted_and_redacted(context, kind, capfd):
    secret = "SYNTHETIC_SECRET_8734"

    async def exercise():
        async with connect(context, kind) as client:
            results = [
                await call(client, "search_policy_documents", {"question": secret}),
                await call(client, "lookup_employee_profile", {"employee_id": "TEST-001"}),
                await call(client, "draft_hr_email", {"recipient_name": secret, "purpose": secret}),
                await call(client, "draft_hr_email", {"recipient_name": secret, "purpose": " "}),
                await call(client, "draft_hr_email", {
                    "recipient_name": secret, "purpose": "synthetic-handler-failure"
                }),
                await call(client, "check_policy_compliance", {
                    "check_id": "out_of_state_prior_approval",
                    "approval_facts": {"approval_timestamp": "2026-01-01T10:00:00Z"},
                }),
                await call(client, "draft_hr_email", {
                    "recipient_name": "Taylor", "purpose": "PTO", secret: secret,
                }),
            ]
            assert [bool(result.isError) for result in results] == [
                False, False, False, True, True, False, True
            ]

    asyncio.run(exercise())
    events = context.events("server")
    assert len(events) == 7
    assert len({event["invocation_id"] for event in events}) == len(events)
    for event in events:
        UUID(event["invocation_id"])
        assert datetime.fromisoformat(event["timestamp"]).utcoffset() is not None
        assert set(event) == {
            "invocation_id", "timestamp", "component", "event_type", "tool", "outcome",
            "classification", "argument_names", "source_ids",
        }
    assert events[0]["outcome"] == "found"
    assert events[0]["source_ids"]
    assert events[3]["classification"] == "INVALID_ARGUMENT"
    assert events[4]["classification"] == "UNKNOWN_ERROR"
    trace_text = context.trace.read_text(encoding="utf-8")
    captured = "".join(capfd.readouterr())
    for forbidden in (secret, "Taylor Fixture", "2026-01-01T10:00:00Z", "Written People Operations"):
        assert forbidden not in trace_text
        assert forbidden not in captured


@pytest.mark.parametrize("arguments", [
    {"recipient_name": "Taylor", "purpose": "PTO"},
    {"recipient_name": "Taylor", "purpose": " "},
    {"recipient_name": "Taylor", "purpose": "synthetic-handler-failure"},
])
def test_server_trace_failure_overrides_success_validation_and_execution(context, arguments):
    async def exercise():
        async with connect(context, "raw", trace=context.root) as client:
            result = await call(client, "draft_hr_email", arguments)
            assert_error(result, "OPERATIONAL_ERROR", "trace_persistence", "trace_persistence_failure")

    asyncio.run(exercise())
    if arguments["purpose"] == " ":
        assert context.calls() == []
    else:
        assert context.calls() == ["draft_hr_email"]
    assert not context.trace.exists()


def test_client_trace_failure_is_explicit(context):
    async def exercise():
        async with MCPClient(
            command=sys.executable,
            args=context.args(),
            trace_sink=TraceSink(context.root),
        ) as client:
            with pytest.raises(ClientError) as error:
                await client.discover()
            assert error.value.classification == "OPERATIONAL_ERROR"
            assert error.value.origin == "trace_persistence"
            assert error.value.code == "trace_persistence_failure"

    asyncio.run(exercise())
    assert context.calls() == []


def test_client_trace_failure_overrides_a_known_client_failure(context):
    class FailUnknownTool(TraceSink):
        def write(self, event):
            if event.outcome == "unknown_tool":
                raise TracePersistenceError("Synthetic failure")
            super().write(event)

    async def exercise():
        async with MCPClient(
            command=sys.executable, args=context.args(), trace_sink=FailUnknownTool(context.trace)
        ) as client:
            with pytest.raises(ClientError) as error:
                await client.call("unknown-tool", {})
            assert error.value.classification == "OPERATIONAL_ERROR"
            assert error.value.origin == "trace_persistence"
            assert error.value.code == "trace_persistence_failure"

    asyncio.run(exercise())


def test_unknown_tool_and_connection_failures_are_traced(context):
    async def exercise():
        async with connect(context, "provided") as client:
            with pytest.raises(ClientError, match="unknown_tool"):
                await client.call("SYNTHETIC_SECRET_UNKNOWN", {})
        with pytest.raises(ClientError, match="transport_failure"):
            async with MCPClient(
                command=str(context.root / "missing-server.exe"),
                trace_sink=TraceSink(context.trace),
            ):
                pytest.fail("unavailable server connected")

    asyncio.run(exercise())
    events = context.events("client")
    assert any(event["outcome"] == "unknown_tool" and event["tool"] is None for event in events)
    assert any(event["outcome"] == "transport_failure" for event in events)
    assert "SYNTHETIC_SECRET_UNKNOWN" not in context.trace.read_text(encoding="utf-8")


def test_discovery_failure_is_traced(context):
    async def exercise():
        async with MCPClient(
            command=sys.executable,
            args=context.args("discovery-error"),
            trace_sink=TraceSink(context.trace),
        ) as client:
            with pytest.raises(ClientError, match="discovery_failure"):
                await client.discover()

    asyncio.run(exercise())
    assert context.events("client")[-1]["outcome"] == "discovery_failure"
    assert "secret" not in context.trace.read_text(encoding="utf-8")


def test_initialization_protocol_error_is_not_inferred_as_transport(context):
    script = (
        "import json,sys; request=json.loads(sys.stdin.readline()); "
        "print(json.dumps({'jsonrpc':'2.0','id':request['id'],"
        "'error':{'code':-32603,'message':'synthetic secret'}}),flush=True); sys.stdin.read()"
    )

    async def exercise():
        with pytest.raises(ClientError) as error:
            async with MCPClient(
                command=sys.executable,
                args=["-c", script],
                trace_sink=TraceSink(context.trace),
            ):
                pytest.fail("initialization should fail")
        assert error.value.classification == "UNCLASSIFIED_ERROR"
        assert error.value.origin is None
        assert error.value.protocol_code == -32603
        assert "secret" not in str(error.value)

    asyncio.run(exercise())
    assert context.events("client")[-1]["classification"] == "UNCLASSIFIED_ERROR"
    assert "secret" not in context.trace.read_text(encoding="utf-8")


@pytest.mark.parametrize("params", [
    {"name": "draft_hr_email", "arguments": "SYNTHETIC_SECRET_INVALID"},
    {"arguments": {"purpose": "SYNTHETIC_SECRET_INVALID"}},
])
def test_malformed_protocol_is_rejected_before_dispatch(context, params):
    async def exercise():
        env = get_default_environment()
        env["HR_MCP_TRACE_PATH"] = str(context.trace)
        process = await asyncio.create_subprocess_exec(
            sys.executable, *context.args(),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            def send(message):
                process.stdin.write((json.dumps(message) + "\n").encode())

            async def receive():
                return json.loads(await asyncio.wait_for(process.stdout.readline(), timeout=20))

            send({
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "synthetic-test", "version": "1"},
                },
            })
            await process.stdin.drain()
            assert (await receive())["id"] == 1
            send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            send({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": params})
            await process.stdin.drain()
            response = await receive()
            assert response["id"] == 2
            assert response["error"]["code"] == -32602
            assert "SYNTHETIC_SECRET_INVALID" not in json.dumps(response)
        finally:
            process.stdin.close()
            await process.stdin.wait_closed()
            await asyncio.wait_for(process.wait(), timeout=20)
            stderr = (await process.stderr.read()).decode()
            assert "SYNTHETIC_SECRET_INVALID" not in stderr

    asyncio.run(exercise())
    assert context.calls() == []
    assert context.events("server") == []

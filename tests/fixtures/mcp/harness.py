"""Isolated stdio harness for the Feature 002 integration tests."""

import json
import shutil
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from hr_mcp.client import MCPClient
from hr_mcp.trace import TraceSink
from hr_rag import ChunkingConfig, build_index
from tests.fixtures.mcp.doubles import DeterministicEmbedder

FIXTURES = Path(__file__).parent


@dataclass
class Context:
    root: Path
    corpus: Path
    index: Path
    baseline: Path
    pin: Path
    trace: Path
    marker: Path

    def args(self, mode="normal", *, index=None, data_dir=None):
        args = [
            "-m", "tests.fixtures.mcp.integration_server",
            str(self.corpus), str(index or self.index), mode,
            "--baseline", str(self.baseline), "--pin", str(self.pin),
            "--marker", str(self.marker),
        ]
        if data_dir is not None:
            args.extend(["--data-dir", str(data_dir)])
        return args

    def events(self, component=None):
        if not self.trace.exists():
            return []
        events = [json.loads(line) for line in self.trace.read_text(encoding="utf-8").splitlines()]
        return [event for event in events if component is None or event["component"] == component]

    def calls(self):
        return self.marker.read_text(encoding="utf-8").splitlines() if self.marker.exists() else []


def build_context(tmp_path):
    corpus = tmp_path / "corpus"
    shutil.copytree(FIXTURES / "policies", corpus)
    baseline = tmp_path / "baseline.json"
    pin = tmp_path / "pin.json"
    shutil.copyfile(FIXTURES / "baseline.json", baseline)
    shutil.copyfile(FIXTURES / "baseline-pin.json", pin)
    context = Context(tmp_path, corpus, tmp_path / "index", baseline, pin,
                      tmp_path / "traces.jsonl", tmp_path / "calls.txt")
    rebuild(context)
    return context


def rebuild(context):
    return build_index(
        context.index,
        corpus_dir=context.corpus,
        embedder=DeterministicEmbedder(),
        chunking_config=ChunkingConfig(),
    )


@asynccontextmanager
async def connect(context, kind, mode="normal", *, index=None, data_dir=None, trace=None):
    args = context.args(mode, index=index, data_dir=data_dir)
    trace_path = trace if trace is not None else context.trace
    if kind == "provided":
        async with MCPClient(command=sys.executable, args=args, trace_sink=TraceSink(trace_path)) as client:
            yield client
    else:
        params = StdioServerParameters(
            command=sys.executable, args=args, env={"HR_MCP_TRACE_PATH": str(trace_path)}
        )
        async with (
            stdio_client(params) as (read, write),
            ClientSession(read, write) as client,
        ):
            await client.initialize()
            await client.list_tools()
            yield client


async def call(client, name, arguments):
    if isinstance(client, MCPClient):
        return await client.call(name, arguments)
    return await client.call_tool(name, arguments)

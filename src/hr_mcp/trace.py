"""Allowlisted, persistent local MCP traces."""

import inspect
import logging
import os
from pathlib import Path

from mcp.shared import session as mcp_session

from .models import TraceEvent


class TracePersistenceError(Exception):
    """A required trace could not be persisted."""


class TraceSink:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    @classmethod
    def from_environment(cls) -> "TraceSink":
        path = os.environ.get("HR_MCP_TRACE_PATH")
        return cls(path if path is not None else Path(".hr_mcp") / "traces.jsonl")

    def write(self, event: TraceEvent) -> None:
        encoded = (event.model_dump_json() + "\n").encode("utf-8")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("ab") as stream:
                written = stream.write(encoded)
                if written != len(encoded):
                    raise OSError("Incomplete trace write.")
                stream.flush()
        except (OSError, ValueError) as exc:
            raise TracePersistenceError("Required trace persistence failed.") from exc


class _SDKRootLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        source = os.path.normcase(os.path.abspath(record.pathname))
        sdk_session = os.path.normcase(os.path.abspath(inspect.getfile(mcp_session)))
        return source != sdk_session


def sanitize_sdk_logging() -> None:
    # SDK session validation also writes request contents directly to the root logger.
    logging.getLogger("mcp").setLevel(logging.CRITICAL + 1)
    root = logging.getLogger()
    if not any(isinstance(item, _SDKRootLogFilter) for item in root.filters):
        root.addFilter(_SDKRootLogFilter())

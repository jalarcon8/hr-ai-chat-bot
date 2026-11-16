"""Explicit Feature 003 initialization and runtime errors."""


class AgentError(Exception):
    """Base error carrying a safe, machine-readable code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class AgentInitializationError(AgentError):
    """The agent could not establish a ready MCP tool catalog."""


class AgentRuntimeError(AgentError):
    """The agent could not complete the current model/tool exchange."""


class ProviderRequestError(AgentRuntimeError):
    """Provider failure with privacy-safe request diagnostics."""

    def __init__(self, code: str, diagnostic: dict[str, object]) -> None:
        super().__init__(code)
        self.diagnostic = diagnostic

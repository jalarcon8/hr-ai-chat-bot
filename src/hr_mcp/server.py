"""MCP stdio server and injectable tool registrations."""

from __future__ import annotations

import inspect
import json
import re
from collections.abc import Awaitable, Callable, Mapping
from functools import cache
from pathlib import Path
from typing import Annotated, Any, Literal

from jsonschema import ValidationError as SchemaValidationError
from jsonschema import validate as validate_schema
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, Field, StrictInt, TypeAdapter, ValidationError

from hr_rag.config import Settings
from hr_rag.index import Embedder, SentenceTransformerEmbedder
from hr_rag.models import EmbeddingError, IndexError

from . import policy, tools
from .data import DataUnavailableError, SyntheticData
from .models import (
    ApprovalFacts,
    ComplianceInput,
    ComplianceResult,
    DraftFound,
    DraftInput,
    EmployeeFound,
    EmployeeInput,
    ErrorDetails,
    ErrorEnvelope,
    EvidenceNotFound,
    NonBlank,
    PTOFound,
    RecordNotFound,
    SearchFound,
    SearchInput,
    SectionFound,
    SectionInput,
    TraceEvent,
)
from .trace import TracePersistenceError, TraceSink, sanitize_sdk_logging

Handler = Callable[[dict[str, Any]], dict[str, Any] | Awaitable[dict[str, Any]]]
TOOL_NAMES = (
    "search_policy_documents",
    "get_policy_section",
    "lookup_employee_profile",
    "check_pto_balance",
    "check_policy_compliance",
    "draft_hr_email",
)


def create_handlers(
    settings: Settings, data: SyntheticData, embedder_factory: Callable[[], Embedder]
) -> dict[str, Handler]:
    @cache
    def embedder() -> Embedder:
        return embedder_factory()

    def search(arguments: dict[str, Any]) -> dict[str, Any]:
        return policy.search_policy_documents(
            arguments["question"], settings.index_dir, embedder=embedder(), k=arguments["k"]
        ).model_dump(mode="json")

    def section(arguments: dict[str, Any]) -> dict[str, Any]:
        return policy.get_policy_section(
            arguments["document_id"], arguments["section"], settings.index_dir
        ).model_dump(mode="json")

    def employee(arguments: dict[str, Any]) -> dict[str, Any]:
        return data.lookup_employee_profile(arguments["employee_id"]).model_dump(mode="json")

    def pto(arguments: dict[str, Any]) -> dict[str, Any]:
        return data.check_pto_balance(arguments["employee_id"]).model_dump(mode="json")

    def compliance(arguments: dict[str, Any]) -> dict[str, Any]:
        return tools.check_policy_compliance(
            arguments["check_id"],
            arguments["approval_facts"],
            index_dir=settings.index_dir,
            corpus_dir=settings.corpus_dir,
        ).model_dump(mode="json")

    def draft(arguments: dict[str, Any]) -> dict[str, Any]:
        return tools.draft_hr_email(
            arguments["recipient_name"], arguments["purpose"], arguments["supporting_details"]
        ).model_dump(mode="json")

    return {
        "search_policy_documents": search,
        "get_policy_section": section,
        "lookup_employee_profile": employee,
        "check_pto_balance": pto,
        "check_policy_compliance": compliance,
        "draft_hr_email": draft,
    }


def create_server(
    handlers: Mapping[str, Handler] | None = None, *, trace_sink: TraceSink | None = None
) -> FastMCP:
    sanitize_sdk_logging()
    server = FastMCP("fictional-hr-tools")
    sink = trace_sink if trace_sink is not None else TraceSink.from_environment()
    if handlers is None:
        settings = Settings.from_environment()
        data = SyntheticData(Path("data") / "employees.json", Path("data") / "pto.json")
        handlers = create_handlers(
            settings,
            data,
            lambda: SentenceTransformerEmbedder(
                settings.embedding_model, revision=settings.embedding_revision
            ),
        )
    registered_handlers = dict(handlers)

    async def dispatch(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        handler = registered_handlers.get(name)
        if handler is None:
            raise RuntimeError("Tool handler is not configured.")
        result = handler(arguments)
        return await result if inspect.isawaitable(result) else result

    @server.tool(structured_output=True)
    async def search_policy_documents(
        question: NonBlank, k: Annotated[StrictInt, Field(gt=0)] = 5
    ) -> dict[str, Any]:
        """Find ranked candidate excerpts from the fictional policy index."""
        return await dispatch("search_policy_documents", {"question": question, "k": k})

    @server.tool(structured_output=True)
    async def get_policy_section(document_id: NonBlank, section: NonBlank) -> dict[str, Any]:
        """Get indexed excerpts for an exact document and section."""
        return await dispatch("get_policy_section", {"document_id": document_id, "section": section})

    @server.tool(structured_output=True)
    async def lookup_employee_profile(employee_id: NonBlank) -> dict[str, Any]:
        """Look up a fictional employee profile."""
        return await dispatch("lookup_employee_profile", {"employee_id": employee_id})

    @server.tool(structured_output=True)
    async def check_pto_balance(employee_id: NonBlank) -> dict[str, Any]:
        """Look up a fictional employee's PTO balance."""
        return await dispatch("check_pto_balance", {"employee_id": employee_id})

    @server.tool(structured_output=True)
    async def check_policy_compliance(
        check_id: Literal["out_of_state_prior_approval"],
        approval_facts: ApprovalFacts | None = None,
    ) -> dict[str, Any]:
        """Evaluate the bounded prior-approval check using caller-supplied facts."""
        facts = None if approval_facts is None else approval_facts.model_dump(exclude_unset=True)
        return await dispatch(
            "check_policy_compliance", {"check_id": check_id, "approval_facts": facts}
        )

    @server.tool(structured_output=True)
    async def draft_hr_email(
        recipient_name: NonBlank, purpose: NonBlank, supporting_details: str = ""
    ) -> dict[str, Any]:
        """Draft a fictional HR email without sending or storing it."""
        return await dispatch(
            "draft_hr_email",
            {
                "recipient_name": recipient_name,
                "purpose": purpose,
                "supporting_details": supporting_details,
            },
        )

    output_schemas = {
        "search_policy_documents": TypeAdapter(SearchFound | EvidenceNotFound).json_schema(),
        "get_policy_section": TypeAdapter(SectionFound | EvidenceNotFound).json_schema(),
        "lookup_employee_profile": TypeAdapter(EmployeeFound | RecordNotFound).json_schema(),
        "check_pto_balance": TypeAdapter(PTOFound | RecordNotFound).json_schema(),
        "check_policy_compliance": ComplianceResult.model_json_schema(),
        "draft_hr_email": DraftFound.model_json_schema(),
    }
    employee_missing = output_schemas["lookup_employee_profile"]["$defs"]["RecordNotFound"]
    employee_missing["properties"]["missing"]["enum"] = ["employee"]
    for schema in output_schemas.values():
        for definition in (schema, *schema.get("$defs", {}).values()):
            properties = definition.get("properties", {})
            if not properties:
                continue
            required = definition.setdefault("required", [])
            for name in ("status", "evidence_kind", "check_id"):
                if name in properties and name not in required:
                    required.append(name)
            if definition.get("title") == "EvidenceNotFound" and "evidence" not in required:
                required.append("evidence")
    input_models: dict[str, type[BaseModel]] = {
        "search_policy_documents": SearchInput,
        "get_policy_section": SectionInput,
        "lookup_employee_profile": EmployeeInput,
        "check_pto_balance": EmployeeInput,
        "check_policy_compliance": ComplianceInput,
        "draft_hr_email": DraftInput,
    }
    registrations = {tool.name: tool for tool in server._tool_manager.list_tools()}
    for tool in server._tool_manager.list_tools():
        tool.parameters["additionalProperties"] = False
        tool.fn_metadata.output_schema = output_schemas[tool.name]

    def failure(details: ErrorDetails) -> CallToolResult:
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text="Tool request failed.")],
            structuredContent=ErrorEnvelope(error=details).model_dump(mode="json"),
        )

    async def request_adapter(name: str, arguments: dict[str, Any]) -> CallToolResult:
        registration = registrations.get(name)
        safe_name = name if registration is not None else None
        allowed = set(input_models[name].model_fields) if registration is not None else set()
        argument_names = sorted(set(arguments) & allowed)
        details: ErrorDetails | None = None
        result: dict[str, Any] | None = None

        if registration is None:
            details = ErrorDetails(
                classification="UNKNOWN_ERROR", origin="request_adapter", code="internal_error"
            )
        else:
            try:
                validate_schema(arguments, registration.parameters)
                request = input_models[name].model_validate(arguments)
            except (SchemaValidationError, ValidationError):
                details = ErrorDetails(
                    classification="INVALID_ARGUMENT",
                    origin="input_validation",
                    code="invalid_argument",
                )
            except Exception:  # noqa: BLE001 - the boundary must classify unexpected failures.
                details = ErrorDetails(
                    classification="UNKNOWN_ERROR", origin="request_adapter", code="internal_error"
                )
            else:
                try:
                    result = await dispatch(name, request.model_dump(mode="json"))
                    validate_schema(result, output_schemas[name])
                except IndexError:
                    details = ErrorDetails(
                        classification="OPERATIONAL_ERROR",
                        origin="tool_execution",
                        code="index_unavailable",
                    )
                except EmbeddingError:
                    details = ErrorDetails(
                        classification="OPERATIONAL_ERROR",
                        origin="tool_execution",
                        code="embedding_failure",
                    )
                except DataUnavailableError:
                    details = ErrorDetails(
                        classification="OPERATIONAL_ERROR",
                        origin="tool_execution",
                        code="data_unavailable",
                    )
                except Exception:  # noqa: BLE001 - handler failures must be sanitized and traced.
                    details = ErrorDetails(
                        classification="UNKNOWN_ERROR",
                        origin="tool_execution",
                        code="internal_error",
                    )

        sources: list[str] = []
        if details is None and result is not None:
            for item in result.get("evidence", []):
                source = item.get("document_id")
                if isinstance(source, str) and re.fullmatch(r"[A-Z]{2,8}-[0-9]{3}", source):
                    sources.append(source)
        if details is None:
            assert result is not None
            outcome = result["status"]
        else:
            outcome = details.classification
        event = TraceEvent(
            component="server",
            event_type="tool_call",
            tool=safe_name,
            outcome=outcome,
            classification=details.classification if details is not None else None,
            argument_names=argument_names,
            source_ids=sorted(set(sources)),
        )
        try:
            sink.write(event)
        except TracePersistenceError:
            return failure(
                ErrorDetails(
                    classification="OPERATIONAL_ERROR",
                    origin="trace_persistence",
                    code="trace_persistence_failure",
                )
            )
        if details is not None:
            return failure(details)
        assert result is not None
        return CallToolResult(
            isError=False,
            content=[TextContent(type="text", text=json.dumps(result, ensure_ascii=False))],
            structuredContent=result,
        )

    # Bypass FastMCP's argument parsing and exception wrapping at the SDK dispatch boundary.
    server._mcp_server.call_tool(validate_input=False)(request_adapter)
    return server


if __name__ == "__main__":
    create_server().run(transport="stdio")

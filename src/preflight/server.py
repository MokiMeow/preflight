"""Thin official MCP v2 server; tool schemas come from the frozen input records."""

import inspect

import anyio
from mcp.server import MCPServer
from mcp.server.mcpserver.tools.base import Tool
from mcp.types import ToolAnnotations

from .models import TOOL_INPUTS, TOOL_OUTPUTS, ToolEnvelope
from .service import RehearsalService

READ_ONLY = {"get_run", "get_source_status", "get_report"}


class SafeTool(Tool):
    """Validate inside the service so SDK error formatting cannot echo input values."""

    async def run(self, arguments, context, convert_result=False):
        result = await self.fn(**arguments)
        return self.fn_metadata.convert_result(result) if convert_result else result


def make_server(service: RehearsalService) -> MCPServer:
    tools: list[Tool] = []
    for name, model in TOOL_INPUTS.items():

        def build_handler(tool_name, input_model, output_model):
            envelope_model = ToolEnvelope[output_model]  # type: ignore[valid-type]

            async def handler(**kwargs):
                return await anyio.to_thread.run_sync(lambda: service.call(tool_name, kwargs))

            handler.__name__ = tool_name
            annotations = {}
            params = []
            for field_name, field in input_model.model_fields.items():
                annotation = field.rebuild_annotation()
                annotations[field_name] = annotation
                params.append(
                    inspect.Parameter(
                        field_name,
                        inspect.Parameter.KEYWORD_ONLY,
                        annotation=annotation,
                        default=inspect.Parameter.empty if field.is_required() else field.default,
                    )
                )
            annotations["return"] = envelope_model
            handler.__annotations__ = annotations
            handler.__signature__ = inspect.Signature(params, return_annotation=envelope_model)
            return handler

        handler = build_handler(name, model, TOOL_OUTPUTS[name])
        tool = Tool.from_function(
            handler,
            name=name,
            structured_output=True,
            description=f"Preflight {name}; server policy and state guards apply.",
            annotations=ToolAnnotations(
                read_only_hint=name in READ_ONLY,
                destructive_hint=name in {"apply_to_clone", "apply_to_demo_source", "cleanup_run"},
                idempotent_hint=name in READ_ONLY,
                open_world_hint=False,
            ),
        )
        # Use strict frozen schema and validation, including unknown field rejection.
        tool.parameters = model.model_json_schema()
        tools.append(SafeTool(**tool.__dict__))
    return MCPServer("preflight", version="0.1.0", log_level="WARNING", tools=tools)


def serve(service: RehearsalService, port: int = 8000):
    make_server(service).run(transport="streamable-http", host="127.0.0.1", port=port)

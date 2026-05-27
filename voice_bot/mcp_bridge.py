import json
from contextlib import AsyncExitStack
from typing import Any

from google.genai import types as genai_types
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


_STRIP_KEYS = {"title", "$schema", "$defs", "definitions", "additionalProperties"}


def _sanitize_schema(schema: Any) -> Any:
    """Strip JSON Schema fields Gemini doesn't accept; collapse Optional anyOf."""
    if not isinstance(schema, dict):
        return schema
    result: dict[str, Any] = {}
    for k, v in schema.items():
        if k in _STRIP_KEYS:
            continue
        if k == "anyOf" and isinstance(v, list):
            non_null = [s for s in v if not (isinstance(s, dict) and s.get("type") == "null")]
            has_null = any(isinstance(s, dict) and s.get("type") == "null" for s in v)
            if len(non_null) == 1 and has_null:
                cleaned = _sanitize_schema(non_null[0])
                if isinstance(cleaned, dict):
                    cleaned["nullable"] = True
                    result.update(cleaned)
                    continue
            result[k] = [_sanitize_schema(s) for s in v]
        elif isinstance(v, dict):
            result[k] = _sanitize_schema(v)
        elif isinstance(v, list):
            result[k] = [_sanitize_schema(i) for i in v]
        else:
            result[k] = v
    return result


def _payload_from_mcp(result: Any) -> dict:
    """Extract a dict payload from an MCP CallToolResult."""
    if getattr(result, "isError", False):
        text = ""
        for block in getattr(result, "content", []) or []:
            text += getattr(block, "text", "") or ""
        return {"ok": False, "error": text or "Tool execution failed"}
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if not text:
            continue
        try:
            return json.loads(text)
        except (ValueError, TypeError):
            return {"ok": True, "text": text}
    return {"ok": True}


class McpBridge:
    def __init__(self, url: str) -> None:
        self._url = url
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def __aenter__(self) -> "McpBridge":
        self._stack = AsyncExitStack()
        read, write, _ = await self._stack.enter_async_context(
            streamablehttp_client(self._url)
        )
        self._session = await self._stack.enter_async_context(
            ClientSession(read, write)
        )
        await self._session.initialize()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._stack is not None:
            await self._stack.aclose()
        self._stack = None
        self._session = None

    async def list_function_declarations(self) -> list[genai_types.FunctionDeclaration]:
        assert self._session is not None
        resp = await self._session.list_tools()
        decls: list[genai_types.FunctionDeclaration] = []
        for tool in resp.tools:
            params = _sanitize_schema(tool.inputSchema) if tool.inputSchema else {"type": "object", "properties": {}}
            decls.append(
                genai_types.FunctionDeclaration(
                    name=tool.name,
                    description=tool.description or "",
                    parameters=params,
                )
            )
        return decls

    async def call(self, name: str, args: dict) -> dict:
        assert self._session is not None
        try:
            result = await self._session.call_tool(name, args or {})
        except Exception as e:
            return {"ok": False, "error": f"MCP call failed: {e}"}
        return _payload_from_mcp(result)

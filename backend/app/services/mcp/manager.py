"""
Connected MCP servers, as tools the model can call.

A remote server's catalog is fetched once, when it is connected or refreshed,
and cached on the connection row. Everything after that reads the cache, so a
chat turn never waits on a `tools/list` round-trip and a server that goes down
between turns degrades to a tool that errors rather than a tile that hangs.

Each server becomes its own integration group, so its tools appear in the Tool
Calling catalog next to AWS with the same switches, the same badges and the
same "a hidden or disabled tool is never offered to the model" guarantee.
"""

import re
from typing import Any, Dict, List

from app.services.mcp import client
from app.store.connections_store import (
    get_connection,
    list_connections,
    set_status,
)

MCP_KIND = "mcp"

# Function names go to the provider, which requires ^[a-zA-Z0-9_-]{1,64}$.
NAME_LIMIT = 64
TOOL_PREFIX = "mcp"


def slugify(text: str, fallback: str = "server") -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    return slug[:20] or fallback


def server_slug(connection: Dict[str, Any]) -> str:
    """The stable, per-server piece of every tool name it contributes.

    Resolved once when the server is connected and kept in its config, because
    tool names are what the disable list stores — recomputing one from a
    renamed label would silently orphan the switch.
    """
    stored = (connection.get("config") or {}).get("slug")
    return stored or slugify(connection.get("label"), connection["id"])


def tool_name(slug: str, remote_name: str) -> str:
    name = f"{TOOL_PREFIX}_{slug}_{re.sub(r'[^a-zA-Z0-9_-]+', '_', remote_name)}"
    return name[:NAME_LIMIT]


def integration_id(conn_id: str) -> str:
    return f"mcp:{conn_id}"


def normalize_schema(input_schema: Any) -> Dict[str, Any]:
    """Coerce a remote inputSchema into the object schema providers require.

    Servers are inconsistent here — some send no schema for a no-argument tool,
    some send a bare `{}`. A malformed one would be rejected by the provider
    for the whole request, taking every other tool down with it.
    """
    if not isinstance(input_schema, dict):
        return {"type": "object", "properties": {}, "required": []}

    schema = dict(input_schema)
    schema["type"] = "object"
    properties = schema.get("properties")
    schema["properties"] = properties if isinstance(properties, dict) else {}
    required = schema.get("required")
    schema["required"] = [r for r in required if isinstance(r, str)] if isinstance(required, list) else []
    return schema


def refresh(conn_id: str) -> Dict[str, Any]:
    """Re-probe one server and cache what it offers.

    Never raises: the failure is recorded on the connection so the UI can show
    why a server is unreachable, and its tools simply stop being listed.
    """
    connection = get_connection(conn_id)
    if connection is None or connection["kind"] != MCP_KIND:
        return {"ok": False, "error": "Unknown MCP server."}

    config = connection["config"]
    try:
        probed = client.probe(config.get("url", ""), config.get("auth_token", ""))
    except client.McpError as e:
        status = {"ok": False, "error": str(e), "tool_count": 0, "tools": []}
        set_status(conn_id, status)
        return status
    except Exception as e:  # noqa: BLE001 - a third party must not take the app down
        status = {"ok": False, "error": f"Unexpected error: {e}", "tool_count": 0, "tools": []}
        set_status(conn_id, status)
        return status

    tools = [
        {
            "name": tool.get("name", ""),
            "description": (tool.get("description") or "").strip(),
            "parameters": normalize_schema(tool.get("inputSchema")),
        }
        for tool in probed["tools"]
        if isinstance(tool, dict) and tool.get("name")
    ]

    status = {
        "ok": True,
        "error": "",
        "server_name": probed["server_name"],
        "server_version": probed["server_version"],
        "tool_count": len(tools),
        "tools": tools,
    }
    set_status(conn_id, status)
    return status


def _make_caller(url: str, auth_token: str, remote_name: str):
    """Bind one remote tool to a callable `run_tool()` can invoke.

    Takes **kwargs because the argument names come from the remote schema and
    are not known here; `run_tool()` skips its keyword filtering for callables
    shaped this way.
    """
    def call_remote(**kwargs):
        try:
            return client.call(url, auth_token, remote_name, kwargs)
        except client.McpError as e:
            return {"error": f"The MCP server could not run {remote_name}: {e}"}

    call_remote.__name__ = f"mcp_{remote_name}"
    return call_remote


def connected_servers() -> List[Dict[str, Any]]:
    """Enabled MCP connections whose last probe succeeded."""
    return [
        c for c in list_connections(MCP_KIND)
        if c["enabled"] and c["status"].get("ok") and c["status"].get("tools")
    ]


def mcp_tools() -> Dict[str, Dict[str, Any]]:
    """Registry-shaped entries for every tool the connected servers expose."""
    entries: Dict[str, Dict[str, Any]] = {}

    for connection in connected_servers():
        config = connection["config"]
        slug = server_slug(connection)
        label = connection["label"] or config.get("url", "MCP server")

        for tool in connection["status"]["tools"]:
            name = tool_name(slug, tool["name"])
            if name in entries:
                continue  # two remote tools collapsing to one name: keep the first

            description = tool["description"] or f"{tool['name']} on the {label} MCP server."
            entries[name] = {
                "schema": {
                    "name": name,
                    # Naming the server helps the model pick between two
                    # servers offering similarly named tools.
                    "description": f"{description} (via the {label} MCP server)"[:1024],
                    "parameters": tool["parameters"],
                },
                "fn": _make_caller(config.get("url", ""), config.get("auth_token", ""), tool["name"]),
                "label": tool["name"],
                "kind": "mcp",
                "integration": integration_id(connection["id"]),
                "demo": False,
                "example": "",
            }

    return entries


def mcp_integrations() -> Dict[str, Dict[str, Any]]:
    """One INTEGRATIONS-shaped group per connected server."""
    groups: Dict[str, Dict[str, Any]] = {}

    for connection in connected_servers():
        label = connection["label"] or connection["config"].get("url", "MCP server")
        server_name = connection["status"].get("server_name") or label
        groups[integration_id(connection["id"])] = {
            "label": label,
            "icon": "mcp",
            "description": f"Tools from the {server_name} MCP server.",
        }

    return groups

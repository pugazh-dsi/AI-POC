"""MCP client: remote servers connected in the UI, surfaced as callable tools."""

from app.services.mcp.manager import (
    mcp_integrations,
    mcp_tools,
    refresh,
    server_slug,
    slugify,
)

__all__ = ["mcp_integrations", "mcp_tools", "refresh", "server_slug", "slugify"]

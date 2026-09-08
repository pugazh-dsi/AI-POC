"""
Connections: the systems the Tool Calling tile reaches out to.

Two kinds, one panel in the UI:

    AWS   one account. Connecting it flips the S3 / CloudWatch tools from the
          fixture account to real, read-only boto3 calls.
    MCP   any number of remote MCP servers. Connecting one pulls its tool
          catalog into the same registry the model is given, so its tools get
          the same switches, badges and disable guarantees as everything else.

🛡️ Credentials go in and never come back out. Every response is built by
`public_view()`, which replaces each secret with a mask — the UI can show that
a key is stored, never what it is.

Provider SDKs and HTTP clients here are synchronous, so each call is run in a
worker thread rather than blocking the event loop for every other request.
"""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.services.connections import aws_client
from app.services.mcp import manager
from app.store.connections_store import (
    AWS_ID,
    delete_connection,
    get_connection,
    list_connections,
    new_connection_id,
    public_view,
    save_connection,
    set_enabled,
    set_status,
)

router = APIRouter()

MCP_KIND = "mcp"


# ── Request bodies ────────────────────────────────────────────

class AwsConnectRequest(BaseModel):
    access_key_id: str
    # Blank means "keep the stored secret", matching how a provider API key
    # behaves — the UI never has the value to send back.
    secret_access_key: str = ""
    session_token: str = ""
    region: str = aws_client.DEFAULT_REGION


class EnabledRequest(BaseModel):
    enabled: bool


class McpConnectRequest(BaseModel):
    label: str
    url: str
    auth_token: str = ""


class McpUpdateRequest(BaseModel):
    label: str | None = None
    url: str | None = None
    auth_token: str | None = None
    enabled: bool | None = None


# ── Shaping ───────────────────────────────────────────────────

def _mcp_view(connection: Dict[str, Any]) -> Dict[str, Any]:
    """One MCP row for the UI: the masked record plus what it contributes.

    `tools` carries the prefixed names the model actually sees, so the row and
    the tool catalog cannot show different names for the same remote tool.
    """
    view = public_view(connection)
    status = connection["status"]
    slug = manager.server_slug(connection)

    view["server_name"] = status.get("server_name", "")
    view["server_version"] = status.get("server_version", "")
    view["connected"] = bool(status.get("ok"))
    view["error"] = status.get("error", "")
    view["tool_count"] = status.get("tool_count", 0)
    view["tools"] = [
        {
            "name": manager.tool_name(slug, tool["name"]),
            "remote_name": tool["name"],
            "description": tool["description"],
        }
        for tool in status.get("tools", [])
    ]
    return view


def _aws_view() -> Dict[str, Any] | None:
    connection = get_connection(AWS_ID)
    if connection is None:
        return None

    view = public_view(connection)
    status = connection["status"]
    view["connected"] = bool(status.get("ok"))
    view["error"] = status.get("error", "")
    view["account"] = status.get("account", "")
    view["arn"] = status.get("arn", "")
    # `enabled` is the user's live/demo switch; `live` is what the tools will
    # actually do on the next question.
    view["live"] = connection["enabled"] and bool(status.get("ok"))
    return view


def _snapshot() -> Dict[str, Any]:
    return {
        "aws": _aws_view(),
        "mcp": [_mcp_view(c) for c in list_connections(MCP_KIND)],
    }


# ── Listing ───────────────────────────────────────────────────

@router.get("/connections")
async def list_all():
    """Everything connected, with every credential masked."""
    return await run_in_threadpool(_snapshot)


# ── AWS ───────────────────────────────────────────────────────

def _connect_aws(request: AwsConnectRequest) -> Dict[str, Any]:
    existing = get_connection(AWS_ID)
    stored = existing["config"] if existing else {}

    secret = request.secret_access_key.strip() or stored.get("secret_access_key", "")
    if not request.access_key_id.strip() or not secret:
        raise ValueError("An access key ID and secret access key are both required.")

    config = {
        "access_key_id": request.access_key_id.strip(),
        "secret_access_key": secret,
        # A blank token clears a previous one rather than keeping it — an
        # expired session token left behind would break every call.
        "session_token": request.session_token.strip(),
        "region": request.region.strip() or aws_client.DEFAULT_REGION,
    }

    # Validate before storing, so a rejected key never becomes the account the
    # tools believe they are connected to.
    identity = aws_client.test_credentials(config)

    save_connection(AWS_ID, "aws", label=f"AWS ({identity['account']})", config=config, enabled=True)
    set_status(AWS_ID, identity)
    return _aws_view()


@router.put("/connections/aws")
async def connect_aws(request: AwsConnectRequest):
    """Store and verify the AWS account the S3 / CloudWatch tools will use.

    The credentials are checked with `sts:GetCallerIdentity` before they are
    written — that call needs no permissions of its own, so it proves the keys
    are valid without the user having to grant anything first.
    """
    try:
        return await run_in_threadpool(_connect_aws, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except aws_client.AwsNotConnected as e:
        raise HTTPException(status_code=400, detail=str(e))


def _test_aws() -> Dict[str, Any]:
    config = aws_client.stored_credentials()
    if config is None:
        raise ValueError("No AWS account is connected.")

    try:
        identity = aws_client.test_credentials(config)
    except ValueError as e:
        set_status(AWS_ID, {"ok": False, "error": str(e)})
        raise

    set_status(AWS_ID, identity)
    return _aws_view()


@router.post("/connections/aws/test")
async def test_aws():
    """Re-check the stored credentials — they may have been rotated or expired."""
    try:
        return await run_in_threadpool(_test_aws)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/connections/aws")
async def toggle_aws(request: EnabledRequest):
    """Switch between the live account and the demo fixture, keeping the keys.

    Turning it off is not a display change: `is_live()` goes false, so the very
    next tool call answers from the fixture account instead of AWS.
    """
    if not await run_in_threadpool(set_enabled, AWS_ID, request.enabled):
        raise HTTPException(status_code=404, detail="No AWS account is connected.")
    return await run_in_threadpool(_aws_view)


@router.delete("/connections/aws")
async def disconnect_aws():
    """Forget the account and its credentials; the tools return to demo data."""
    if not await run_in_threadpool(delete_connection, AWS_ID):
        raise HTTPException(status_code=404, detail="No AWS account is connected.")
    return {"message": "AWS account disconnected.", "aws": None}


# ── MCP ───────────────────────────────────────────────────────

def _unique_slug(label: str, conn_id: str, exclude: str = "") -> str:
    """A tool-name prefix no other connected server is already using."""
    base = manager.slugify(label, conn_id)
    taken = {
        manager.server_slug(c)
        for c in list_connections(MCP_KIND)
        if c["id"] != exclude
    }
    if base not in taken:
        return base
    return f"{base}_{conn_id[:4]}"[:24]


def _connect_mcp(request: McpConnectRequest) -> Dict[str, Any]:
    url = request.url.strip()
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("The server URL must start with http:// or https://.")

    label = request.label.strip() or url
    conn_id = new_connection_id()

    save_connection(
        conn_id,
        MCP_KIND,
        label=label,
        config={
            "url": url,
            "auth_token": request.auth_token.strip(),
            # Fixed at connect time: tool names are what the disable list
            # stores, so they must not move when the label is edited later.
            "slug": _unique_slug(label, conn_id),
        },
        enabled=True,
    )

    # A server that cannot be reached is still saved, with the failure on the
    # row — the user can fix the URL or token and retry rather than retyping.
    manager.refresh(conn_id)
    return _mcp_view(get_connection(conn_id))


@router.post("/connections/mcp")
async def connect_mcp(request: McpConnectRequest):
    """Add an MCP server and pull in its tool catalog.

    The catalog is fetched once here and cached on the row, so a chat turn
    never waits on a `tools/list` round-trip.
    """
    try:
        return await run_in_threadpool(_connect_mcp, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _update_mcp(conn_id: str, request: McpUpdateRequest) -> Dict[str, Any]:
    connection = get_connection(conn_id)
    if connection is None or connection["kind"] != MCP_KIND:
        raise LookupError("Unknown MCP server.")

    config: Dict[str, Any] = {}
    if request.url is not None:
        url = request.url.strip()
        if not url.lower().startswith(("http://", "https://")):
            raise ValueError("The server URL must start with http:// or https://.")
        config["url"] = url
    if request.auth_token is not None:
        config["auth_token"] = request.auth_token.strip()

    save_connection(
        conn_id,
        MCP_KIND,
        label=(request.label.strip() if request.label else connection["label"]),
        config=config,
        enabled=connection["enabled"] if request.enabled is None else request.enabled,
    )

    # Where the server is reached has changed, so the cached catalog may not be
    # this server's any more.
    if config:
        manager.refresh(conn_id)

    return _mcp_view(get_connection(conn_id))


@router.patch("/connections/mcp/{conn_id}")
async def update_mcp(conn_id: str, request: McpUpdateRequest):
    """Rename, re-point, re-authorize or switch off one server.

    Switching it off removes its tools from the schemas the model is given, not
    just from the list.
    """
    try:
        return await run_in_threadpool(_update_mcp, conn_id, request)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _refresh_mcp(conn_id: str) -> Dict[str, Any]:
    connection = get_connection(conn_id)
    if connection is None or connection["kind"] != MCP_KIND:
        raise LookupError("Unknown MCP server.")
    manager.refresh(conn_id)
    return _mcp_view(get_connection(conn_id))


@router.post("/connections/mcp/{conn_id}/refresh")
async def refresh_mcp(conn_id: str):
    """Re-read one server's catalog — it may have gained or lost tools."""
    try:
        return await run_in_threadpool(_refresh_mcp, conn_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/connections/mcp/{conn_id}")
async def disconnect_mcp(conn_id: str):
    """Remove a server and every tool it contributed."""
    connection = await run_in_threadpool(get_connection, conn_id)
    if connection is None or connection["kind"] != MCP_KIND:
        raise HTTPException(status_code=404, detail="Unknown MCP server.")

    await run_in_threadpool(delete_connection, conn_id)
    return {"message": f"Disconnected {connection['label']}.", "id": conn_id}

"""
A minimal synchronous MCP client, speaking the Streamable HTTP transport.

Enough of the protocol to do what the Tool Calling tile needs and no more:
discover a remote server's tools and invoke one. It is deliberately hand-rolled
rather than pulling in the async `mcp` SDK, because `run_tool()` is called
synchronously from a worker thread and an async client would have to be bridged
back across the event loop on every call.

    initialize                -> server info + capabilities (+ Mcp-Session-Id)
    notifications/initialized -> ack, required before any request
    tools/list                -> the catalog
    tools/call                -> run one tool

Each operation opens its own short-lived session. That costs one extra
round-trip per call and buys statelessness: nothing to keep alive, reconnect or
invalidate when a server restarts between turns.

⚠️ An MCP server is a third party. Everything it returns — tool descriptions
included — is untrusted data, handled the same way tool results already are:
reported on, never obeyed. The tool-calling system prompt already says so.
"""

import json
from typing import Any, Dict, List

import httpx

PROTOCOL_VERSION = "2025-06-18"

CLIENT_INFO = {"name": "document-qa-bot", "version": "1.1.0"}

# A server that stalls must fail as data, not hold the SSE stream open.
CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 30.0


class McpError(Exception):
    """Any failure reaching or talking to an MCP server."""


def _headers(auth_token: str = "", session_id: str = "") -> Dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        # Streamable HTTP servers may answer either way; accept both.
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": PROTOCOL_VERSION,
    }
    if auth_token:
        # Accept a raw token or a full scheme the user pasted ("Bearer x").
        token = auth_token.strip()
        headers["Authorization"] = token if " " in token else f"Bearer {token}"
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    return headers


def _parse_sse(body: str) -> Dict[str, Any] | None:
    """Pull the first JSON-RPC message out of an SSE response body.

    A streamable-HTTP server may answer a single request with an event stream
    rather than a JSON body; the reply we want is the first `data:` payload
    that parses as a JSON-RPC message.
    """
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload:
            continue
        try:
            message = json.loads(payload)
        except ValueError:
            continue
        if isinstance(message, dict) and ("result" in message or "error" in message):
            return message
    return None


def _rpc(
    client: httpx.Client,
    url: str,
    method: str,
    params: Dict[str, Any] | None,
    auth_token: str,
    session_id: str,
    request_id: int,
) -> tuple[Dict[str, Any], str]:
    """One JSON-RPC request. Returns (result, session_id)."""
    body = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        body["params"] = params

    try:
        response = client.post(url, json=body, headers=_headers(auth_token, session_id))
    except httpx.HTTPError as e:
        raise McpError(f"Could not reach the server: {e}") from e

    session_id = response.headers.get("Mcp-Session-Id", session_id)

    if response.status_code == 401:
        raise McpError("The server rejected the token (401). Check the auth token.")
    if response.status_code == 404:
        raise McpError("No MCP endpoint at that URL (404). Check the path.")
    if response.status_code >= 400:
        raise McpError(f"The server returned HTTP {response.status_code}.")

    content_type = response.headers.get("content-type", "")
    if "text/event-stream" in content_type:
        message = _parse_sse(response.text)
        if message is None:
            raise McpError("The server's event stream carried no JSON-RPC reply.")
    else:
        try:
            message = response.json()
        except ValueError as e:
            raise McpError(
                "The server did not return JSON — is this a Streamable HTTP MCP endpoint?"
            ) from e

    if isinstance(message, list):  # a batched reply
        message = next((m for m in message if isinstance(m, dict)), {})

    if "error" in message:
        detail = message["error"]
        raise McpError(detail.get("message") if isinstance(detail, dict) else str(detail))

    return message.get("result", {}) or {}, session_id


def _notify(
    client: httpx.Client, url: str, method: str, auth_token: str, session_id: str
) -> None:
    """Fire-and-forget notification. A server that ignores it is not an error."""
    try:
        client.post(
            url,
            json={"jsonrpc": "2.0", "method": method},
            headers=_headers(auth_token, session_id),
        )
    except httpx.HTTPError:
        pass


class McpSession:
    """One initialized connection, used for a single operation then closed."""

    def __init__(self, url: str, auth_token: str = ""):
        self.url = url.strip()
        self.auth_token = auth_token or ""
        self.session_id = ""
        self.server_info: Dict[str, Any] = {}
        self.capabilities: Dict[str, Any] = {}
        self._client: httpx.Client | None = None
        self._next_id = 0

    def __enter__(self) -> "McpSession":
        if not self.url.lower().startswith(("http://", "https://")):
            raise McpError("The server URL must start with http:// or https://.")

        self._client = httpx.Client(
            timeout=httpx.Timeout(READ_TIMEOUT, connect=CONNECT_TIMEOUT),
            follow_redirects=True,
        )

        result = self._call("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": CLIENT_INFO,
        })
        self.server_info = result.get("serverInfo", {}) or {}
        self.capabilities = result.get("capabilities", {}) or {}

        _notify(self._client, self.url, "notifications/initialized",
                self.auth_token, self.session_id)
        return self

    def __exit__(self, *exc) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _call(self, method: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        self._next_id += 1
        result, self.session_id = _rpc(
            self._client, self.url, method, params,
            self.auth_token, self.session_id, self._next_id,
        )
        return result

    def list_tools(self) -> List[Dict[str, Any]]:
        """Every tool the server offers, following `nextCursor` pagination."""
        tools: List[Dict[str, Any]] = []
        cursor = None

        # Bounded: a server that keeps handing back cursors must not spin here.
        for _ in range(10):
            params = {"cursor": cursor} if cursor else {}
            result = self._call("tools/list", params)
            tools.extend(result.get("tools", []) or [])
            cursor = result.get("nextCursor")
            if not cursor:
                break

        return tools

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._call("tools/call", {"name": name, "arguments": arguments or {}})


def probe(url: str, auth_token: str = "") -> Dict[str, Any]:
    """Connect, read the catalog, disconnect. Used by the connect/test button."""
    with McpSession(url, auth_token) as session:
        tools = session.list_tools()
        return {
            "server_name": session.server_info.get("name", ""),
            "server_version": session.server_info.get("version", ""),
            "tools": tools,
        }


def call(url: str, auth_token: str, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke one remote tool and flatten its content blocks for the model."""
    with McpSession(url, auth_token) as session:
        result = session.call_tool(name, arguments)

    texts: List[str] = []
    other: List[Dict[str, Any]] = []

    for block in result.get("content", []) or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            texts.append(block.get("text", ""))
        else:
            other.append(block)

    payload: Dict[str, Any] = {}

    # Prefer the server's structured output when it sends one; otherwise parse
    # the text block if it happens to be JSON, so the model sees fields rather
    # than a stringified blob.
    if isinstance(result.get("structuredContent"), dict):
        payload["result"] = result["structuredContent"]
    elif texts:
        joined = "\n".join(t for t in texts if t)
        try:
            payload["result"] = json.loads(joined)
        except ValueError:
            payload["result"] = joined

    if other:
        payload["content"] = other
    if result.get("isError"):
        payload["error"] = payload.pop("result", "The MCP tool reported an error.")

    return payload or {"result": "The tool returned no content."}

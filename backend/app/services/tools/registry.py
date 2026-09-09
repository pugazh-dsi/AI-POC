"""The tool catalog: one entry per callable the model may invoke.

Adding a tool means adding one entry here — the provider schemas, the executor
and the UI list are all derived from this dict, so there is no second place to
keep in sync.

Each entry:
    schema       JSON-Schema function definition sent to the provider
    fn           the Python callable, taking the schema's arguments as kwargs
    label        human name for the UI
    kind         "local" (pure computation) | "api" (external call) |
                 "rag" (index) | "integration" (a connected system)
    integration  which group in INTEGRATIONS it belongs to
    demo         True when the tool returns simulated data, not a live system.
                 May be a zero-argument callable when that depends on runtime
                 state — the AWS tools are demo only until an account is
                 connected under Connections.
    example      a sample question that should trigger this tool

Tools can be switched off. A disabled tool is not in the schemas handed to the
model and `run_tool()` refuses it, so hiding one in the UI genuinely removes
the capability rather than only the row. The set of disabled names lives in
`app_state` so it survives a restart.

A whole INTEGRATIONS group can also be marked `hidden`, which takes its tools
out of the tile altogether: not listed, not offered to the model, not runnable.
That is a build-time choice about what this tile demonstrates, unlike the
per-tool switch, which the user flips at runtime.

Not every tool is written here. A connected MCP server contributes its own,
discovered at connect time and merged in by `all_tools()` — so the catalog,
the schemas and the executor pick them up without a second code path. Look at
`all_tools()` / `all_integrations()`, not the literals, when asking what the
model can currently reach.
"""

import inspect
import json
from typing import Any, Dict, List

from app.services.mcp import mcp_integrations, mcp_tools
from app.services.tools import calculator, documents, weather
from app.services.tools.integrations import aws, google, salesforce, snowflake
from app.store.settings_store import get_state, set_state

DISABLED_TOOLS_KEY = "disabled_tools"

# Every tool contributed by an MCP server is named `mcp_<server>_<tool>`.
MCP_TOOL_PREFIX = "mcp"

# The groups the Tool Calling tile lists. `icon` is the slug the frontend's
# IntegrationIcon maps to a brand mark; an unknown slug falls back to a plug.
# `hidden` removes the whole group from the tile — see `visible_tools()`.
INTEGRATIONS: Dict[str, Dict[str, Any]] = {
    "core": {
        "label": "Built-in",
        "icon": "core",
        "description": "Tools that run inside this app — no external account needed.",
        # The tile demonstrates the enterprise integrations, so weather /
        # calculator / the document tools are kept out of it. They stay
        # registered (and the RAG tile still uses retrieval directly) — flip
        # this to False to bring the group back into the catalog.
        "hidden": True,
    },
    "aws": {
        "label": "AWS",
        "icon": "aws",
        "description": "S3 storage and CloudWatch metrics from the connected AWS account.",
    },
    # Built and tested, staged behind the flag until they are switched on for
    # the demo — flip `hidden` to False (or delete the line) to bring one back.
    "snowflake": {
        "label": "Snowflake",
        "icon": "snowflake",
        "description": "Browse the warehouse and run read-only SELECT queries.",
        "hidden": True,
    },
    "google": {
        "label": "Google Workspace",
        "icon": "google",
        "description": "Search Drive files and read the Calendar.",
        "hidden": True,
    },
    "salesforce": {
        "label": "Salesforce",
        "icon": "salesforce",
        "description": "Accounts, pipeline opportunities and contacts from CRM.",
        "hidden": True,
    },
}

TOOLS: Dict[str, Dict[str, Any]] = {
    # ── Built-in ──────────────────────────────────────────────
    "get_weather": {
        "schema": weather.SCHEMA,
        "fn": weather.get_weather,
        "label": "Weather",
        "kind": "api",
        "integration": "core",
        "demo": False,
        "example": "What's the weather in Chennai right now?",
    },
    "calculator": {
        "schema": calculator.SCHEMA,
        "fn": calculator.calculate,
        "label": "Calculator",
        "kind": "local",
        "integration": "core",
        "demo": False,
        "example": "What is 1250 * 1.08 squared?",
    },
    "search_documents": {
        "schema": documents.SEARCH_SCHEMA,
        "fn": documents.search_documents,
        "label": "Search documents",
        "kind": "rag",
        "integration": "core",
        "demo": False,
        "example": "What do my documents say about launch dates?",
    },
    "list_documents": {
        "schema": documents.LIST_SCHEMA,
        "fn": documents.list_documents,
        "label": "List documents",
        "kind": "rag",
        "integration": "core",
        "demo": False,
        "example": "Which documents have I uploaded?",
    },

    # ── AWS ───────────────────────────────────────────────────
    "aws_list_s3_buckets": {
        "schema": aws.LIST_BUCKETS_SCHEMA,
        "fn": aws.list_s3_buckets,
        "label": "List S3 buckets",
        "kind": "integration",
        "integration": "aws",
        "demo": aws.is_demo,
        "example": "Which S3 buckets do we have and how much data is in them?",
    },
    "aws_list_s3_objects": {
        "schema": aws.LIST_OBJECTS_SCHEMA,
        "fn": aws.list_s3_objects,
        "label": "List S3 objects",
        "kind": "integration",
        "integration": "aws",
        "demo": aws.is_demo,
        "example": "What's stored under raw/events/ in acme-prod-data-lake?",
    },
    "aws_read_s3_object": {
        "schema": aws.READ_OBJECT_SCHEMA,
        "fn": aws.read_s3_object,
        "label": "Read S3 file",
        "kind": "integration",
        "integration": "aws",
        "demo": aws.is_demo,
        "example": "What are the line items on the invoice stored in S3?",
    },
    "aws_cloudwatch_metric": {
        "schema": aws.CLOUDWATCH_SCHEMA,
        "fn": aws.get_cloudwatch_metric,
        "label": "CloudWatch metric",
        "kind": "integration",
        "integration": "aws",
        "demo": aws.is_demo,
        "example": "How has CPU utilisation looked over the last 24 hours?",
    },

    # ── Snowflake ─────────────────────────────────────────────
    "snowflake_list_tables": {
        "schema": snowflake.LIST_TABLES_SCHEMA,
        "fn": snowflake.list_tables,
        "label": "List tables",
        "kind": "integration",
        "integration": "snowflake",
        "demo": True,
        "example": "What tables are in our Snowflake warehouse?",
    },
    "snowflake_describe_table": {
        "schema": snowflake.DESCRIBE_TABLE_SCHEMA,
        "fn": snowflake.describe_table,
        "label": "Describe table",
        "kind": "integration",
        "integration": "snowflake",
        "demo": True,
        "example": "What columns does REVENUE_MONTHLY have?",
    },
    "snowflake_run_query": {
        "schema": snowflake.RUN_QUERY_SCHEMA,
        "fn": snowflake.run_query,
        "label": "Run query",
        "kind": "integration",
        "integration": "snowflake",
        "demo": True,
        "example": "What was our revenue by region over the last few months?",
    },

    # ── Google Workspace ──────────────────────────────────────
    "google_search_drive": {
        "schema": google.SEARCH_DRIVE_SCHEMA,
        "fn": google.search_drive,
        "label": "Search Drive",
        "kind": "integration",
        "integration": "google",
        "demo": True,
        "example": "Find the revenue model spreadsheet in Drive.",
    },
    "google_list_calendar_events": {
        "schema": google.CALENDAR_SCHEMA,
        "fn": google.list_calendar_events,
        "label": "Calendar events",
        "kind": "integration",
        "integration": "google",
        "demo": True,
        "example": "What meetings do I have in the next three days?",
    },

    # ── Salesforce ────────────────────────────────────────────
    "salesforce_search_accounts": {
        "schema": salesforce.SEARCH_ACCOUNTS_SCHEMA,
        "fn": salesforce.search_accounts,
        "label": "Search accounts",
        "kind": "integration",
        "integration": "salesforce",
        "demo": True,
        "example": "Which accounts do we have in healthcare?",
    },
    "salesforce_search_opportunities": {
        "schema": salesforce.SEARCH_OPPORTUNITIES_SCHEMA,
        "fn": salesforce.search_opportunities,
        "label": "Search pipeline",
        "kind": "integration",
        "integration": "salesforce",
        "demo": True,
        "example": "What's in the pipeline and what is it worth?",
    },
    "salesforce_get_contact": {
        "schema": salesforce.GET_CONTACT_SCHEMA,
        "fn": salesforce.get_contact,
        "label": "Get contact",
        "kind": "integration",
        "integration": "salesforce",
        "demo": True,
        "example": "Who is our contact at Northwind Traders?",
    },
}


# ── Visibility ────────────────────────────────────────────────

def resolve_demo(tool: Dict[str, Any]) -> bool:
    """A tool's `demo` flag, calling it when it depends on runtime state."""
    value = tool.get("demo")
    return bool(value() if callable(value) else value)


def all_tools() -> Dict[str, Dict[str, Any]]:
    """Everything registered right now: the built-ins plus connected MCP servers.

    MCP entries are rebuilt from the cached catalog on each call rather than
    held in a module global, so connecting or disconnecting a server takes
    effect on the next turn with nothing to invalidate.
    """
    return {**TOOLS, **mcp_tools()}


def all_integrations() -> Dict[str, Dict[str, Any]]:
    """The built-in groups plus one per connected MCP server."""
    return {**INTEGRATIONS, **mcp_integrations()}


def hidden_integrations() -> set:
    """Groups this tile does not expose at all."""
    return {key for key, meta in all_integrations().items() if meta.get("hidden")}


def visible_tools() -> Dict[str, Dict[str, Any]]:
    """Tools belonging to a group the tile exposes.

    Everything downstream — the catalog, the schemas, the executor — is built
    from this rather than TOOLS, so a hidden group cannot leak into the tile
    through one of them.
    """
    hidden = hidden_integrations()
    return {
        name: tool for name, tool in all_tools().items()
        if tool["integration"] not in hidden
    }


# ── Enable / disable ──────────────────────────────────────────

def disabled_tools() -> set:
    """Names the user has switched off, from app_state.

    A corrupt or hand-edited value must not take the tile down, so anything
    unparseable is treated as "nothing disabled".
    """
    try:
        stored = json.loads(get_state(DISABLED_TOOLS_KEY, "[]"))
    except (ValueError, TypeError):
        return set()

    if not isinstance(stored, list):
        return set()

    # Drop names of tools that no longer exist, so a removed tool cannot leave
    # a stale entry that silently disables a future tool of the same name.
    # MCP names are kept regardless: a server that is unreachable this minute
    # has not been removed, and losing the entry would switch its tools back on
    # behind the user's back when it reconnects.
    known = all_tools()
    return {
        name for name in stored
        if name in known or name.startswith(f"{MCP_TOOL_PREFIX}_")
    }


def is_enabled(name: str) -> bool:
    """Whether the tile currently offers this tool: visible AND switched on."""
    return name in visible_tools() and name not in disabled_tools()


def set_tool_enabled(name: str, enabled: bool) -> bool:
    """Switch one tool on or off.

    Returns False if the name is unknown or belongs to a hidden group — the UI
    never shows those, so a request for one is not a tool the user can see.
    """
    if name not in visible_tools():
        return False

    current = disabled_tools()
    if enabled:
        current.discard(name)
    else:
        current.add(name)

    set_state(DISABLED_TOOLS_KEY, json.dumps(sorted(current)))
    return True


def enabled_tools() -> Dict[str, Dict[str, Any]]:
    off = disabled_tools()
    return {name: tool for name, tool in visible_tools().items() if name not in off}


# ── Views over the catalog ────────────────────────────────────

def get_tool_schemas() -> List[Dict]:
    """Function definitions to hand the provider — enabled tools only.

    A disabled tool is not offered to the model at all, so switching one off in
    the UI removes the capability rather than just the row.
    """
    return [tool["schema"] for tool in enabled_tools().values()]


def describe_tools() -> List[Dict]:
    """Catalog for the UI — the same source of truth the model sees.

    Disabled tools are still listed (with `enabled: False`) so they can be
    switched back on; only `get_tool_schemas()` filters them out. Tools in a
    hidden group are not listed at all.
    """
    off = disabled_tools()
    return [
        {
            "name": name,
            "label": tool["label"],
            "kind": tool["kind"],
            "integration": tool["integration"],
            "demo": resolve_demo(tool),
            "enabled": name not in off,
            "description": tool["schema"]["description"],
            "parameters": tool["schema"]["parameters"],
            "example": tool["example"],
        }
        for name, tool in visible_tools().items()
    ]


def describe_integrations() -> List[Dict]:
    """The groups the UI renders, each with its tool counts.

    A hidden group is skipped, so it appears nowhere in the tile.
    """
    off = disabled_tools()
    hidden = hidden_integrations()
    registered = all_tools()
    groups = []

    for key, meta in all_integrations().items():
        if key in hidden:
            continue
        names = [n for n, t in registered.items() if t["integration"] == key]
        if not names:
            continue
        groups.append({
            "id": key,
            "label": meta["label"],
            "icon": meta["icon"],
            "description": meta["description"],
            "tool_count": len(names),
            "enabled_count": len([n for n in names if n not in off]),
            "demo": all(resolve_demo(registered[n]) for n in names),
        })

    return groups


def run_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool by name.

    Never raises: a tool failure is returned as data so the model can explain it
    and keep the turn alive. A raised exception would drop the SSE stream and
    leave the UI hanging with no finish frame.
    """
    tool = visible_tools().get(name)
    if tool is None:
        # Covers both a name that does not exist and one in a hidden group —
        # neither is available on this tile.
        return {"error": f"Unknown tool: {name}"}

    # Belt and braces: a disabled tool is never in the schemas, but a model
    # replaying an earlier turn could still name one.
    if not is_enabled(name):
        return {"error": f"The {name} tool is currently switched off."}

    if not isinstance(args, dict):
        return {"error": f"{name} expected an object of arguments."}

    # Models occasionally invent parameters; drop them rather than crashing on
    # an unexpected keyword argument. A tool declaring **kwargs — every MCP
    # tool does, since its parameter names live on the remote server — accepts
    # whatever the schema promised, so filtering there would delete every
    # argument instead of the invented ones.
    parameters = inspect.signature(tool["fn"]).parameters.values()
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters):
        cleaned = dict(args)
    else:
        accepted = {p.name for p in parameters}
        cleaned = {k: v for k, v in args.items() if k in accepted}

    try:
        return tool["fn"](**cleaned)
    except TypeError as e:
        return {"error": f"Invalid arguments for {name}: {e}"}
    except Exception as e:  # noqa: BLE001 - a broken tool must not kill the stream
        print(f"Tool '{name}' failed: {e}")
        return {"error": f"{name} failed: {e}"}

"""The tool catalog: one entry per callable the model may invoke.

Adding a tool means adding one entry here — the provider schemas, the executor
and the UI list are all derived from this dict, so there is no second place to
keep in sync.

Each entry:
    schema   JSON-Schema function definition sent to the provider
    fn       the Python callable, taking the schema's arguments as kwargs
    label    human name for the UI
    kind     "local" (pure computation) | "api" (external call) | "rag" (index)
    example  a sample question that should trigger this tool
"""

import inspect
from typing import Any, Callable, Dict, List

from app.services.tools import calculator, documents, weather

TOOLS: Dict[str, Dict[str, Any]] = {
    "get_weather": {
        "schema": weather.SCHEMA,
        "fn": weather.get_weather,
        "label": "Weather",
        "kind": "api",
        "example": "What's the weather in Chennai right now?",
    },
    "calculator": {
        "schema": calculator.SCHEMA,
        "fn": calculator.calculate,
        "label": "Calculator",
        "kind": "local",
        "example": "What is 1250 * 1.08 squared?",
    },
    "search_documents": {
        "schema": documents.SEARCH_SCHEMA,
        "fn": documents.search_documents,
        "label": "Search documents",
        "kind": "rag",
        "example": "What do my documents say about launch dates?",
    },
    "list_documents": {
        "schema": documents.LIST_SCHEMA,
        "fn": documents.list_documents,
        "label": "List documents",
        "kind": "rag",
        "example": "Which documents have I uploaded?",
    },
}


def get_tool_schemas() -> List[Dict]:
    """Function definitions to hand the provider."""
    return [tool["schema"] for tool in TOOLS.values()]


def describe_tools() -> List[Dict]:
    """Catalog for the UI — the same source of truth the model sees."""
    return [
        {
            "name": name,
            "label": tool["label"],
            "kind": tool["kind"],
            "description": tool["schema"]["description"],
            "parameters": tool["schema"]["parameters"],
            "example": tool["example"],
        }
        for name, tool in TOOLS.items()
    ]


def run_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool by name.

    Never raises: a tool failure is returned as data so the model can explain it
    and keep the turn alive. A raised exception would drop the SSE stream and
    leave the UI hanging with no finish frame.
    """
    tool = TOOLS.get(name)
    if tool is None:
        return {"error": f"Unknown tool: {name}"}

    if not isinstance(args, dict):
        return {"error": f"{name} expected an object of arguments."}

    # Models occasionally invent parameters; drop them rather than crashing on
    # an unexpected keyword argument.
    accepted = set(inspect.signature(tool["fn"]).parameters)
    cleaned = {k: v for k, v in args.items() if k in accepted}

    try:
        return tool["fn"](**cleaned)
    except TypeError as e:
        return {"error": f"Invalid arguments for {name}: {e}"}
    except Exception as e:  # noqa: BLE001 - a broken tool must not kill the stream
        print(f"Tool '{name}' failed: {e}")
        return {"error": f"{name} failed: {e}"}

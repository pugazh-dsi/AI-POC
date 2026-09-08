"""Arithmetic evaluation with no `eval`.

The model is very willing to hand this tool arbitrary strings, so the
expression is parsed into an AST and only a whitelist of node types is walked.
`eval()` here would be a remote code execution hole reachable from the chat box.
"""

import ast
import math
import operator

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}

# Only pure numeric helpers — nothing that touches the filesystem or the process
_FUNCTIONS = {
    "abs": abs, "round": round, "min": min, "max": max, "sum": sum,
    "sqrt": math.sqrt, "floor": math.floor, "ceil": math.ceil,
    "log": math.log, "log10": math.log10, "log2": math.log2, "exp": math.exp,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "degrees": math.degrees, "radians": math.radians,
}

_CONSTANTS = {"pi": math.pi, "e": math.e, "tau": math.tau}

# Guards against a one-character expression pinning a CPU core (2**99999999)
MAX_EXPONENT = 1000


def _evaluate(node):
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        raise ValueError("Only numeric literals are allowed.")

    if isinstance(node, ast.BinOp):
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        left, right = _evaluate(node.left), _evaluate(node.right)
        if op is operator.pow and abs(right) > MAX_EXPONENT:
            raise ValueError(f"Exponent too large (limit {MAX_EXPONENT}).")
        return op(left, right)

    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        return op(_evaluate(node.operand))

    if isinstance(node, ast.Name):
        if node.id in _CONSTANTS:
            return _CONSTANTS[node.id]
        raise ValueError(f"Unknown name: {node.id}")

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS:
            raise ValueError("Only basic math functions are allowed.")
        if node.keywords:
            raise ValueError("Keyword arguments are not supported.")
        return _FUNCTIONS[node.func.id](*[_evaluate(a) for a in node.args])

    if isinstance(node, (ast.List, ast.Tuple)):
        return [_evaluate(e) for e in node.elts]

    raise ValueError(f"Unsupported expression element: {type(node).__name__}")


def calculate(expression: str) -> dict:
    """Evaluate an arithmetic expression and return the result as JSON."""
    expression = (expression or "").strip()
    if not expression:
        return {"error": "No expression provided."}
    if len(expression) > 500:
        return {"error": "Expression is too long (limit 500 characters)."}

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as e:
        return {"expression": expression, "error": f"Could not parse the expression: {e.msg}"}

    try:
        result = _evaluate(tree)
    except ZeroDivisionError:
        return {"expression": expression, "error": "Division by zero."}
    except (ValueError, TypeError, OverflowError) as e:
        return {"expression": expression, "error": str(e)}

    if isinstance(result, float):
        result = round(result, 10)
        if result.is_integer():
            result = int(result)

    return {"expression": expression, "result": result}


SCHEMA = {
    "name": "calculator",
    "description": (
        "Evaluate an arithmetic expression and return the exact numeric result. "
        "Use this for ANY calculation rather than working it out yourself. "
        "Supports + - * / // % **, parentheses, and the functions sqrt, abs, round, "
        "min, max, floor, ceil, log, log10, log2, exp, sin, cos, tan, degrees, radians, "
        "plus the constants pi and e."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The expression to evaluate, e.g. '(1250 * 1.08) ** 2' or 'sqrt(144) + pi'.",
            }
        },
        "required": ["expression"],
    },
}

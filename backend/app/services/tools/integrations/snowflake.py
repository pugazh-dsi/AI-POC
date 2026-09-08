"""Snowflake integration: browse the warehouse and run read-only queries.

Demo data today. Going live means replacing each body with a
snowflake-connector-python cursor execution — the read-only guard below stays
either way, because the SQL string is written by the model from a user's
sentence and must never be able to mutate a warehouse.
"""

import re

DEMO_NOTE = (
    "This is DEMO data from a simulated Snowflake warehouse, not the user's "
    "real data. Say so when reporting these figures."
)

DATABASE = "ACME_ANALYTICS"
SCHEMA_NAME = "PUBLIC"
WAREHOUSE = "COMPUTE_WH"

_TABLES = {
    "CUSTOMERS": {
        "rows": 48_211,
        "bytes": 812_004_992,
        "columns": [
            ("CUSTOMER_ID", "NUMBER(38,0)", False),
            ("COMPANY_NAME", "VARCHAR(255)", False),
            ("INDUSTRY", "VARCHAR(100)", True),
            ("REGION", "VARCHAR(50)", True),
            ("MRR_USD", "NUMBER(12,2)", True),
            ("SIGNED_AT", "TIMESTAMP_NTZ", True),
            ("CHURNED_AT", "TIMESTAMP_NTZ", True),
        ],
    },
    "ORDERS": {
        "rows": 1_902_884,
        "bytes": 6_112_884_002,
        "columns": [
            ("ORDER_ID", "NUMBER(38,0)", False),
            ("CUSTOMER_ID", "NUMBER(38,0)", False),
            ("ORDER_TOTAL_USD", "NUMBER(12,2)", False),
            ("STATUS", "VARCHAR(30)", False),
            ("PLACED_AT", "TIMESTAMP_NTZ", False),
        ],
    },
    "PRODUCT_USAGE": {
        "rows": 84_112_009,
        "bytes": 41_882_004_118,
        "columns": [
            ("EVENT_ID", "VARCHAR(36)", False),
            ("CUSTOMER_ID", "NUMBER(38,0)", False),
            ("FEATURE", "VARCHAR(100)", False),
            ("EVENT_COUNT", "NUMBER(38,0)", False),
            ("EVENT_DATE", "DATE", False),
        ],
    },
    "REVENUE_MONTHLY": {
        "rows": 1_284,
        "bytes": 4_118_002,
        "columns": [
            ("MONTH", "DATE", False),
            ("REGION", "VARCHAR(50)", False),
            ("REVENUE_USD", "NUMBER(14,2)", False),
            ("NEW_CUSTOMERS", "NUMBER(38,0)", False),
            ("CHURNED_CUSTOMERS", "NUMBER(38,0)", False),
        ],
    },
}

# The canned result set a SELECT comes back with. Real enough to reason over,
# small enough not to crowd the conversation.
_SAMPLE_ROWS = {
    "REVENUE_MONTHLY": [
        {"MONTH": "2026-04-01", "REGION": "AMER", "REVENUE_USD": 1_842_119.40, "NEW_CUSTOMERS": 118, "CHURNED_CUSTOMERS": 22},
        {"MONTH": "2026-05-01", "REGION": "AMER", "REVENUE_USD": 1_918_004.10, "NEW_CUSTOMERS": 131, "CHURNED_CUSTOMERS": 19},
        {"MONTH": "2026-06-01", "REGION": "AMER", "REVENUE_USD": 2_004_881.75, "NEW_CUSTOMERS": 127, "CHURNED_CUSTOMERS": 25},
        {"MONTH": "2026-07-01", "REGION": "EMEA", "REVENUE_USD": 1_204_772.90, "NEW_CUSTOMERS": 88, "CHURNED_CUSTOMERS": 14},
        {"MONTH": "2026-08-01", "REGION": "EMEA", "REVENUE_USD": 1_311_408.20, "NEW_CUSTOMERS": 94, "CHURNED_CUSTOMERS": 17},
        {"MONTH": "2026-08-01", "REGION": "APAC", "REVENUE_USD": 742_118.60, "NEW_CUSTOMERS": 61, "CHURNED_CUSTOMERS": 9},
    ],
    "CUSTOMERS": [
        {"CUSTOMER_ID": 10041, "COMPANY_NAME": "Northwind Traders", "INDUSTRY": "Retail", "REGION": "AMER", "MRR_USD": 18_400.00},
        {"CUSTOMER_ID": 10088, "COMPANY_NAME": "Initech Systems", "INDUSTRY": "Software", "REGION": "AMER", "MRR_USD": 42_100.00},
        {"CUSTOMER_ID": 10192, "COMPANY_NAME": "Umbrella Health", "INDUSTRY": "Healthcare", "REGION": "EMEA", "MRR_USD": 31_250.00},
        {"CUSTOMER_ID": 10233, "COMPANY_NAME": "Globex Manufacturing", "INDUSTRY": "Industrial", "REGION": "APAC", "MRR_USD": 27_900.00},
        {"CUSTOMER_ID": 10310, "COMPANY_NAME": "Soylent Foods", "INDUSTRY": "CPG", "REGION": "AMER", "MRR_USD": 12_750.00},
    ],
    "ORDERS": [
        {"ORDER_ID": 880014, "CUSTOMER_ID": 10041, "ORDER_TOTAL_USD": 4_820.00, "STATUS": "FULFILLED", "PLACED_AT": "2026-09-06T14:02:11"},
        {"ORDER_ID": 880015, "CUSTOMER_ID": 10088, "ORDER_TOTAL_USD": 19_400.00, "STATUS": "FULFILLED", "PLACED_AT": "2026-09-06T16:41:03"},
        {"ORDER_ID": 880021, "CUSTOMER_ID": 10192, "ORDER_TOTAL_USD": 8_115.50, "STATUS": "PENDING", "PLACED_AT": "2026-09-07T09:18:44"},
        {"ORDER_ID": 880030, "CUSTOMER_ID": 10310, "ORDER_TOTAL_USD": 2_240.00, "STATUS": "CANCELLED", "PLACED_AT": "2026-09-07T11:55:02"},
    ],
    "PRODUCT_USAGE": [
        {"FEATURE": "dashboard_view", "EVENT_COUNT": 1_284_119, "EVENT_DATE": "2026-09-07"},
        {"FEATURE": "report_export", "EVENT_COUNT": 88_402, "EVENT_DATE": "2026-09-07"},
        {"FEATURE": "api_query", "EVENT_COUNT": 412_887, "EVENT_DATE": "2026-09-07"},
    ],
}

# Anything that could change state. Checked before the statement is "executed",
# so the guard is already in place when a real cursor replaces the demo path.
_WRITE_STATEMENT = re.compile(
    r"\b(insert|update|delete|merge|drop|truncate|alter|create|grant|revoke|"
    r"copy|put|remove|call|execute|use)\b",
    re.IGNORECASE,
)

MAX_ROWS = 50


def list_tables(database: str = "", schema: str = "") -> dict:
    """Tables in the warehouse. Live equivalent: SHOW TABLES IN SCHEMA."""
    return {
        "database": (database or DATABASE).upper(),
        "schema": (schema or SCHEMA_NAME).upper(),
        "warehouse": WAREHOUSE,
        "count": len(_TABLES),
        "tables": [
            {
                "name": name,
                "row_count": spec["rows"],
                "bytes": spec["bytes"],
                "column_count": len(spec["columns"]),
            }
            for name, spec in _TABLES.items()
        ],
        "demo_data": True,
        "note": DEMO_NOTE,
    }


def describe_table(table: str) -> dict:
    """Column definitions for one table. Live equivalent: DESCRIBE TABLE."""
    table = (table or "").strip().upper()
    if not table:
        return {"error": "No table name provided.", "available_tables": list(_TABLES), "demo_data": True}

    spec = _TABLES.get(table)
    if spec is None:
        return {
            "error": f"Table '{table}' does not exist in {DATABASE}.{SCHEMA_NAME}.",
            "available_tables": list(_TABLES),
            "demo_data": True,
        }

    return {
        "database": DATABASE,
        "schema": SCHEMA_NAME,
        "table": table,
        "row_count": spec["rows"],
        "bytes": spec["bytes"],
        "columns": [
            {"name": name, "type": type_, "nullable": nullable}
            for name, type_, nullable in spec["columns"]
        ],
        "demo_data": True,
        "note": DEMO_NOTE,
    }


def run_query(sql: str, limit: int = 10) -> dict:
    """Run a read-only SELECT. Live equivalent: cursor.execute(sql).

    The statement is model-generated from a user sentence, so anything that
    could write is refused before execution — the same guard the live version
    needs, in place from the start.
    """
    sql = (sql or "").strip().rstrip(";")
    if not sql:
        return {"error": "No SQL provided.", "demo_data": True}

    if not sql.lower().lstrip("( ").startswith(("select", "with")):
        return {
            "error": "Only read-only SELECT statements are allowed.",
            "sql": sql,
            "demo_data": True,
        }

    # A second statement after a semicolon would slip past the prefix check.
    if ";" in sql:
        return {
            "error": "Only a single statement may be run at a time.",
            "sql": sql,
            "demo_data": True,
        }

    if _WRITE_STATEMENT.search(sql):
        return {
            "error": "The query contains a statement that could modify data; it was refused.",
            "sql": sql,
            "demo_data": True,
        }

    try:
        limit = max(1, min(int(limit or 10), MAX_ROWS))
    except (TypeError, ValueError):
        limit = 10

    # Which canned result set to hand back: the first known table named in the SQL.
    upper = sql.upper()
    table = next((name for name in _TABLES if name in upper), None)
    if table is None:
        return {
            "sql": sql,
            "row_count": 0,
            "rows": [],
            "demo_data": True,
            "note": (
                "The demo warehouse has no table matching that query. "
                f"Available tables: {', '.join(_TABLES)}."
            ),
        }

    rows = _SAMPLE_ROWS.get(table, [])[:limit]

    return {
        "sql": sql,
        "warehouse": WAREHOUSE,
        "table": table,
        "row_count": len(rows),
        "columns": list(rows[0]) if rows else [],
        "rows": rows,
        "demo_data": True,
        "note": DEMO_NOTE,
    }


LIST_TABLES_SCHEMA = {
    "name": "snowflake_list_tables",
    "description": (
        "List the tables available in the connected Snowflake warehouse with "
        "their row counts and sizes. Use this first when the user asks what "
        "data exists in Snowflake, before writing a query."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "database": {"type": "string", "description": f"Database name. Defaults to {DATABASE}."},
            "schema": {"type": "string", "description": f"Schema name. Defaults to {SCHEMA_NAME}."},
        },
        "required": [],
    },
}

DESCRIBE_TABLE_SCHEMA = {
    "name": "snowflake_describe_table",
    "description": (
        "Show the columns, types and row count of one Snowflake table. Use this "
        "to learn a table's shape before writing a query against it."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "table": {"type": "string", "description": "Table name, e.g. 'REVENUE_MONTHLY'."},
        },
        "required": ["table"],
    },
}

RUN_QUERY_SCHEMA = {
    "name": "snowflake_run_query",
    "description": (
        "Run a read-only SELECT against the Snowflake warehouse and return the "
        "rows. Use for questions about revenue, customers, orders or product "
        "usage. Only SELECT is permitted — any statement that writes is "
        "refused. Call snowflake_describe_table first if unsure of the columns."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "A single read-only SELECT statement, no trailing semicolon.",
            },
            "limit": {
                "type": "integer",
                "description": f"Maximum rows to return (1-{MAX_ROWS}). Defaults to 10.",
            },
        },
        "required": ["sql"],
    },
}

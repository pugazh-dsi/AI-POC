"""Enterprise integration tools — AWS, Snowflake, Google Workspace, Salesforce.

Every function here returns **demo data**. The shape of the response, the
parameters and the error handling are exactly what the real SDK call would
produce, so wiring the real thing later means replacing one function body —
the schema, the registry entry and the UI stay untouched.

Two rules every integration module follows:

1. Each result carries ``"demo_data": True`` and a ``note`` saying so, because
   the tool-calling system prompt tells the model to report what a tool
   returned exactly. Without the marker the model would present invented
   figures as if they came from the user's real account.
2. A failure is returned as data (``{"error": ...}``), never raised —
   ``run_tool()`` depends on it and a raised exception drops the SSE stream.
"""

from app.services.tools.integrations import aws, google, salesforce, snowflake

__all__ = ["aws", "google", "salesforce", "snowflake"]

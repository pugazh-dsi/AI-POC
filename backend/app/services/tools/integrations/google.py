"""Google Workspace integration: Drive search and Calendar.

Demo data today. Going live means an OAuth flow plus google-api-python-client
calls (`drive.files().list`, `calendar.events().list`) — the schemas and the
result shape below already match what those return.
"""

from datetime import datetime, timedelta, timezone

DEMO_NOTE = (
    "This is DEMO data from a simulated Google Workspace account, not the "
    "user's real Drive or Calendar. Say so when reporting these items."
)

ACCOUNT = "demo.user@acme.example"

_FILES = [
    {
        "id": "1AbCdEf_prod_roadmap",
        "name": "FY27 Product Roadmap.gdoc",
        "mime_type": "application/vnd.google-apps.document",
        "owner": "priya.raman@acme.example",
        "modified": "2026-09-05T11:24:00Z",
        "size_kb": 184,
        "shared": True,
        "link": "https://docs.google.com/document/d/1AbCdEf_prod_roadmap",
    },
    {
        "id": "1GhIjKl_q3_revenue",
        "name": "Q3 Revenue Model.gsheet",
        "mime_type": "application/vnd.google-apps.spreadsheet",
        "owner": "demo.user@acme.example",
        "modified": "2026-09-07T16:02:00Z",
        "size_kb": 902,
        "shared": True,
        "link": "https://docs.google.com/spreadsheets/d/1GhIjKl_q3_revenue",
    },
    {
        "id": "1MnOpQr_arch_review",
        "name": "Platform Architecture Review.pdf",
        "mime_type": "application/pdf",
        "owner": "sam.oyelaran@acme.example",
        "modified": "2026-08-28T09:41:00Z",
        "size_kb": 3_412,
        "shared": False,
        "link": "https://drive.google.com/file/d/1MnOpQr_arch_review",
    },
    {
        "id": "1StUvWx_onboarding",
        "name": "Customer Onboarding Playbook.gdoc",
        "mime_type": "application/vnd.google-apps.document",
        "owner": "demo.user@acme.example",
        "modified": "2026-07-19T13:15:00Z",
        "size_kb": 244,
        "shared": True,
        "link": "https://docs.google.com/document/d/1StUvWx_onboarding",
    },
    {
        "id": "1YzAbCd_board_deck",
        "name": "Board Deck September.gslides",
        "mime_type": "application/vnd.google-apps.presentation",
        "owner": "priya.raman@acme.example",
        "modified": "2026-09-08T07:30:00Z",
        "size_kb": 6_118,
        "shared": True,
        "link": "https://docs.google.com/presentation/d/1YzAbCd_board_deck",
    },
]

# Offsets from "now" so the calendar always looks current, however long the demo
# sits unused.
_EVENTS = [
    (2, 60, "Pipeline review", ["priya.raman@acme.example", "sam.oyelaran@acme.example"], "Meet — https://meet.google.com/abc-defg-hij"),
    (5, 30, "1:1 with Priya", ["priya.raman@acme.example"], "Meet — https://meet.google.com/klm-nopq-rst"),
    (26, 90, "Architecture deep dive", ["sam.oyelaran@acme.example", "dev-team@acme.example"], "Room 4B"),
    (30, 45, "Northwind Traders — renewal call", ["j.okafor@northwind.example"], "Meet — https://meet.google.com/uvw-xyza-bcd"),
    (52, 60, "Board prep", ["priya.raman@acme.example"], "Room 1A"),
    (74, 30, "Sprint planning", ["dev-team@acme.example"], "Meet — https://meet.google.com/efg-hijk-lmn"),
]


def search_drive(query: str = "", limit: int = 5) -> dict:
    """Search Drive. Live equivalent: drive.files().list(q=...)."""
    try:
        limit = max(1, min(int(limit or 5), 25))
    except (TypeError, ValueError):
        limit = 5

    needle = (query or "").strip().lower()
    matches = [
        f for f in _FILES
        if not needle
        or needle in f["name"].lower()
        or needle in f["owner"].lower()
        or needle in f["mime_type"].lower()
    ]

    return {
        "account": ACCOUNT,
        "query": query or "(all files)",
        "count": len(matches[:limit]),
        "files": matches[:limit],
        "demo_data": True,
        "note": (
            DEMO_NOTE if matches
            else f"No file in the demo Drive matches '{query}'. " + DEMO_NOTE
        ),
    }


def list_calendar_events(days: int = 7, limit: int = 10) -> dict:
    """Upcoming calendar events. Live equivalent: calendar.events().list()."""
    try:
        days = max(1, min(int(days or 7), 60))
    except (TypeError, ValueError):
        days = 7

    try:
        limit = max(1, min(int(limit or 10), 25))
    except (TypeError, ValueError):
        limit = 10

    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=days)

    events = []
    for hours_ahead, minutes, title, attendees, location in _EVENTS:
        start = now + timedelta(hours=hours_ahead)
        if start > horizon:
            continue
        events.append({
            "title": title,
            "start": start.replace(second=0, microsecond=0).isoformat().replace("+00:00", "Z"),
            "end": (start + timedelta(minutes=minutes)).replace(second=0, microsecond=0)
                    .isoformat().replace("+00:00", "Z"),
            "duration_minutes": minutes,
            "attendees": attendees,
            "location": location,
        })

    return {
        "account": ACCOUNT,
        "window_days": days,
        "count": len(events[:limit]),
        "events": events[:limit],
        "demo_data": True,
        "note": DEMO_NOTE,
    }


SEARCH_DRIVE_SCHEMA = {
    "name": "google_search_drive",
    "description": (
        "Search the connected Google Drive for files by name, owner or type, "
        "returning the file name, owner, last-modified time and a link. Use for "
        "questions about documents, spreadsheets or decks stored in Drive."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Text to match against file names and owners. Omit to list recent files.",
            },
            "limit": {"type": "integer", "description": "How many files to return (1-25). Defaults to 5."},
        },
        "required": [],
    },
}

CALENDAR_SCHEMA = {
    "name": "google_list_calendar_events",
    "description": (
        "List upcoming Google Calendar events with their times, attendees and "
        "location. Use for questions about the user's schedule, meetings or "
        "availability."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "days": {"type": "integer", "description": "How many days ahead to look (1-60). Defaults to 7."},
            "limit": {"type": "integer", "description": "How many events to return (1-25). Defaults to 10."},
        },
        "required": [],
    },
}

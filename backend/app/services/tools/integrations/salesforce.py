"""Salesforce CRM integration: accounts, opportunities and contacts.

Demo data today. Going live means a simple-salesforce client and SOQL queries
against the same objects — the field names below are the standard ones, so the
model's questions carry over unchanged.

The three tools share one fictional org, so an account found by
salesforce_search_accounts really does own the opportunities and contacts the
other two return.
"""

DEMO_NOTE = (
    "This is DEMO data from a simulated Salesforce org, not the user's real "
    "CRM. Say so when reporting these records."
)

ORG = "Acme Corp (Demo Sandbox)"

_ACCOUNTS = [
    {
        "id": "0011x00000AbCdE",
        "name": "Northwind Traders",
        "industry": "Retail",
        "annual_revenue_usd": 84_000_000,
        "employees": 1_200,
        "billing_country": "United States",
        "owner": "Priya Raman",
        "type": "Customer - Direct",
        "open_opportunities": 2,
    },
    {
        "id": "0011x00000FgHiJ",
        "name": "Initech Systems",
        "industry": "Software",
        "annual_revenue_usd": 210_000_000,
        "employees": 3_400,
        "billing_country": "United States",
        "owner": "Sam Oyelaran",
        "type": "Customer - Direct",
        "open_opportunities": 1,
    },
    {
        "id": "0011x00000KlMnO",
        "name": "Umbrella Health",
        "industry": "Healthcare",
        "annual_revenue_usd": 512_000_000,
        "employees": 8_900,
        "billing_country": "United Kingdom",
        "owner": "Priya Raman",
        "type": "Prospect",
        "open_opportunities": 1,
    },
    {
        "id": "0011x00000PqRsT",
        "name": "Globex Manufacturing",
        "industry": "Industrial",
        "annual_revenue_usd": 1_100_000_000,
        "employees": 22_000,
        "billing_country": "Singapore",
        "owner": "Sam Oyelaran",
        "type": "Customer - Channel",
        "open_opportunities": 0,
    },
]

_OPPORTUNITIES = [
    {
        "id": "0061x00000AaBbC",
        "name": "Northwind — Platform renewal FY27",
        "account": "Northwind Traders",
        "stage": "Negotiation/Review",
        "amount_usd": 480_000,
        "probability": 75,
        "close_date": "2026-10-15",
        "owner": "Priya Raman",
        "next_step": "Legal review of the MSA amendment",
    },
    {
        "id": "0061x00000DdEeF",
        "name": "Northwind — Analytics add-on",
        "account": "Northwind Traders",
        "stage": "Proposal/Price Quote",
        "amount_usd": 120_000,
        "probability": 50,
        "close_date": "2026-11-30",
        "owner": "Priya Raman",
        "next_step": "Send revised pricing",
    },
    {
        "id": "0061x00000GgHhI",
        "name": "Initech — Enterprise expansion",
        "account": "Initech Systems",
        "stage": "Value Proposition",
        "amount_usd": 950_000,
        "probability": 30,
        "close_date": "2027-01-20",
        "owner": "Sam Oyelaran",
        "next_step": "Technical deep dive with their platform team",
    },
    {
        "id": "0061x00000JjKkL",
        "name": "Umbrella Health — Pilot",
        "account": "Umbrella Health",
        "stage": "Qualification",
        "amount_usd": 75_000,
        "probability": 20,
        "close_date": "2026-12-05",
        "owner": "Priya Raman",
        "next_step": "Security questionnaire returned",
    },
    {
        "id": "0061x00000MmNnO",
        "name": "Globex — Multi-region rollout",
        "account": "Globex Manufacturing",
        "stage": "Closed Won",
        "amount_usd": 1_400_000,
        "probability": 100,
        "close_date": "2026-08-29",
        "owner": "Sam Oyelaran",
        "next_step": "Kickoff scheduled",
    },
]

_CONTACTS = [
    {
        "id": "0031x00000AaaBb",
        "name": "Jane Okafor",
        "title": "VP Engineering",
        "email": "j.okafor@northwind.example",
        "phone": "+1 415 555 0142",
        "account": "Northwind Traders",
        "last_activity": "2026-09-04",
    },
    {
        "id": "0031x00000CccDd",
        "name": "Marcus Bell",
        "title": "CFO",
        "email": "m.bell@initech.example",
        "phone": "+1 212 555 0188",
        "account": "Initech Systems",
        "last_activity": "2026-08-30",
    },
    {
        "id": "0031x00000EeeFf",
        "name": "Aisha Karim",
        "title": "Head of Data Platform",
        "email": "a.karim@umbrellahealth.example",
        "phone": "+44 20 7946 0102",
        "account": "Umbrella Health",
        "last_activity": "2026-09-06",
    },
    {
        "id": "0031x00000GggHh",
        "name": "Wei Chen",
        "title": "Director of Operations",
        "email": "w.chen@globex.example",
        "phone": "+65 6555 0177",
        "account": "Globex Manufacturing",
        "last_activity": "2026-09-01",
    },
]

STAGES = sorted({o["stage"] for o in _OPPORTUNITIES})


def search_accounts(query: str = "", industry: str = "", limit: int = 5) -> dict:
    """Accounts matching a name or industry. Live equivalent: SOQL on Account."""
    try:
        limit = max(1, min(int(limit or 5), 25))
    except (TypeError, ValueError):
        limit = 5

    needle = (query or "").strip().lower()
    sector = (industry or "").strip().lower()

    matches = [
        a for a in _ACCOUNTS
        if (not needle or needle in a["name"].lower() or needle in a["owner"].lower())
        and (not sector or sector == a["industry"].lower())
    ]

    return {
        "org": ORG,
        "query": query or "(all accounts)",
        "industry_filter": industry or "any",
        "count": len(matches[:limit]),
        "accounts": matches[:limit],
        "demo_data": True,
        "note": (
            DEMO_NOTE if matches
            else "No account in the demo org matches that search. " + DEMO_NOTE
        ),
    }


def search_opportunities(
    account: str = "", stage: str = "", limit: int = 5
) -> dict:
    """Pipeline opportunities. Live equivalent: SOQL on Opportunity."""
    try:
        limit = max(1, min(int(limit or 5), 25))
    except (TypeError, ValueError):
        limit = 5

    account_needle = (account or "").strip().lower()
    stage_needle = (stage or "").strip().lower()

    matches = [
        o for o in _OPPORTUNITIES
        if (not account_needle or account_needle in o["account"].lower())
        and (not stage_needle or stage_needle in o["stage"].lower())
    ]

    if stage_needle and not matches:
        return {
            "org": ORG,
            "count": 0,
            "opportunities": [],
            "known_stages": STAGES,
            "demo_data": True,
            "note": f"No opportunity is in a stage matching '{stage}'. " + DEMO_NOTE,
        }

    shown = matches[:limit]

    return {
        "org": ORG,
        "account_filter": account or "any",
        "stage_filter": stage or "any",
        "count": len(shown),
        "total_amount_usd": sum(o["amount_usd"] for o in shown),
        "weighted_amount_usd": round(
            sum(o["amount_usd"] * o["probability"] / 100 for o in shown), 2
        ),
        "opportunities": shown,
        "demo_data": True,
        "note": DEMO_NOTE,
    }


def get_contact(name_or_email: str) -> dict:
    """One contact by name or email. Live equivalent: SOQL on Contact."""
    needle = (name_or_email or "").strip().lower()
    if not needle:
        return {
            "error": "No contact name or email provided.",
            "known_contacts": [c["name"] for c in _CONTACTS],
            "demo_data": True,
        }

    match = next(
        (
            c for c in _CONTACTS
            if needle in c["name"].lower()
            or needle in c["email"].lower()
            or needle in c["account"].lower()
        ),
        None,
    )

    if match is None:
        return {
            "error": f"No contact found matching '{name_or_email}'.",
            "known_contacts": [c["name"] for c in _CONTACTS],
            "demo_data": True,
        }

    related = [o for o in _OPPORTUNITIES if o["account"] == match["account"]]

    return {
        "org": ORG,
        "contact": match,
        "open_opportunities": [
            {"name": o["name"], "stage": o["stage"], "amount_usd": o["amount_usd"]}
            for o in related
            if o["stage"] != "Closed Won"
        ],
        "demo_data": True,
        "note": DEMO_NOTE,
    }


SEARCH_ACCOUNTS_SCHEMA = {
    "name": "salesforce_search_accounts",
    "description": (
        "Search Salesforce accounts by company name, owner or industry, "
        "returning revenue, headcount, account owner and open-opportunity "
        "count. Use for questions about customers, prospects or accounts in CRM."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Company or owner name to match. Omit to list all accounts."},
            "industry": {"type": "string", "description": "Optional exact industry filter, e.g. 'Retail'."},
            "limit": {"type": "integer", "description": "How many accounts to return (1-25). Defaults to 5."},
        },
        "required": [],
    },
}

SEARCH_OPPORTUNITIES_SCHEMA = {
    "name": "salesforce_search_opportunities",
    "description": (
        "Search the Salesforce sales pipeline, returning each opportunity's "
        "stage, amount, probability, close date and next step, plus the total "
        "and probability-weighted value. Use for questions about deals, "
        "pipeline, forecast or what is closing."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "account": {"type": "string", "description": "Optional account name to filter by."},
            "stage": {
                "type": "string",
                "description": "Optional stage filter, e.g. " + ", ".join(f"'{s}'" for s in STAGES) + ".",
            },
            "limit": {"type": "integer", "description": "How many opportunities to return (1-25). Defaults to 5."},
        },
        "required": [],
    },
}

GET_CONTACT_SCHEMA = {
    "name": "salesforce_get_contact",
    "description": (
        "Look up one Salesforce contact by name, email or account, returning "
        "their title, contact details, last activity and the open "
        "opportunities on their account. Use when asked who to contact at a "
        "company or for a person's details."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "name_or_email": {
                "type": "string",
                "description": "Contact name, email address, or their company name.",
            },
        },
        "required": ["name_or_email"],
    },
}

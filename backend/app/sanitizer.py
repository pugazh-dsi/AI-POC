import re

from app.config import MAX_QUESTION_LENGTH

# Patterns that attempt to override system instructions
INJECTION_PATTERNS = re.compile(
    r"(ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|prompts|rules)|"
    r"disregard\s+(your|all|the)\s+(instructions|rules|guidelines)|"
    r"you\s+are\s+now\s+a|"
    r"new\s+instructions?:|"
    r"system\s*prompt|"
    r"reveal\s+(your|the)\s+(prompt|instructions|rules)|"
    r"act\s+as\s+if\s+you\s+have\s+no\s+restrictions|"
    r"pretend\s+(you\s+are|to\s+be)|"
    r"forget\s+(everything|all|your\s+instructions))",
    re.IGNORECASE,
)


def sanitize_question(question: str) -> str:
    """Clean and validate user input."""
    # Strip whitespace and control characters
    question = question.strip()
    question = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", question)

    # Enforce length limit
    if len(question) > MAX_QUESTION_LENGTH:
        question = question[:MAX_QUESTION_LENGTH]

    return question


def detect_injection(question: str) -> bool:
    """Check if the question contains prompt injection attempts."""
    return bool(INJECTION_PATTERNS.search(question))

from app.services.guardrails.engine import evaluate


def test_malformed_extraction_fails_closed_without_crashing():
    result = evaluate("not-a-dict")

    assert result["status"] in {"non_compliant", "incomplete"}
    assert result["blocked"] is True
    assert result["summary"]["failed"] >= 1 or result["summary"]["not_evaluable"] >= 1

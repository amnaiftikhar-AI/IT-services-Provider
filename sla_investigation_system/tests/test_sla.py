from datetime import datetime, timezone, timedelta
from app.services.sla_service import calculate_sla, calculate_risk

def test_sla_deadlines_and_risk(sample_ticket, sample_policy):
    now = datetime.now(timezone.utc)
    result = calculate_sla(sample_ticket, sample_policy, now=now)
    assert result["response_deadline"]
    assert result["resolution_deadline"]
    assert result["response_remaining_minutes"] < 0
    assert result["resolution_remaining_minutes"] > 0
    assert result["response_breached"] is True
    assert result["resolution_breached"] is False

def test_risk_levels():
    assert calculate_risk(-1, True, False) == "Breached"
    assert calculate_risk(10, False, False) == "Critical"
    assert calculate_risk(25, False, False) == "High"
    assert calculate_risk(50, False, False) == "Medium"
    assert calculate_risk(100, False, False) == "Low"

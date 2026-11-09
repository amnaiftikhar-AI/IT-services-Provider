import pytest
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

@pytest.fixture
def sample_ticket():
    return SimpleNamespace(
        created_at=datetime.now(timezone.utc) - timedelta(minutes=100),
        paused_minutes=0,
        response_at=None,
        resolved_at=None
    )

@pytest.fixture
def sample_policy():
    return SimpleNamespace(
        name="Critical SLA Policy",
        version=1,
        response_minutes=15,
        resolution_minutes=120,
        business_hours_only=False
    )

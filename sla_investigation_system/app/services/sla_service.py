from datetime import datetime, timedelta, timezone

def add_sla_minutes(start, minutes, business_hours_only=False):
    if business_hours_only:
        raise NotImplementedError("Business-hours calendars must be configured before enabling this policy.")
    return start + timedelta(minutes=minutes)

def calculate_sla(ticket, policy, now=None):
    now = now or datetime.now(timezone.utc)
    created = ticket.created_at
    response_deadline = add_sla_minutes(created, policy.response_minutes) 
    resolution_deadline = add_sla_minutes(created, policy.resolution_minutes)
    paused = ticket.paused_minutes or 0
    response_deadline += timedelta(minutes=paused)
    resolution_deadline += timedelta(minutes=paused)
    response_remaining = (response_deadline - now).total_seconds() / 60
    resolution_remaining = (resolution_deadline - now).total_seconds() / 60
    if ticket.response_at:
        response_breached = False
    else:
        response_breached = response_remaining < 0
    if ticket.resolved_at:
        resolution_breached = (ticket.resolved_at > resolution_deadline)
    else:
        resolution_breached = resolution_remaining < 0
    risk = calculate_risk(resolution_remaining, resolution_breached, ticket.resolved_at is not None)
    return {
        "response_deadline": response_deadline.isoformat(),
        "resolution_deadline": resolution_deadline.isoformat(),
        "response_remaining_minutes": round(response_remaining, 2),
        "resolution_remaining_minutes": round(resolution_remaining, 2),
        "response_breached": response_breached,
        "resolution_breached": resolution_breached,
        "risk_level": risk,
        "policy_name": policy.name,
        "policy_version": policy.version
    }

def calculate_risk(remaining, breached, resolved):
    if breached:
        return "Breached"
    if resolved:
        return "Resolved"
    if remaining <= 15:
        return "Critical"
    if remaining <= 30:
        return "High"
    if remaining <= 60:
        return "Medium"
    return "Low"

from datetime import datetime, timedelta, timezone
from app.models import Asset, SLAPolicy, Ticket, HistoricalIncident

def seed_data(db):
    if db.query(Ticket).count() > 0:
        return
    assets = [
        Asset(asset_code="DB-SERVER-01", asset_type="Database Server", environment="Production", criticality="High", description="Primary production database"),
        Asset(asset_code="APP-SERVER-02", asset_type="Application Server", environment="Production", criticality="High", description="Customer application server"),
        Asset(asset_code="LAPTOP-014", asset_type="Employee Laptop", environment="Office", criticality="Low", description="Employee workstation")
    ]
    db.add_all(assets)
    db.flush()
    policies = [
        SLAPolicy(name="Critical SLA Policy", priority="Critical", response_minutes=15, resolution_minutes=120),
        SLAPolicy(name="High SLA Policy", priority="High", response_minutes=30, resolution_minutes=240),
        SLAPolicy(name="Medium SLA Policy", priority="Medium", response_minutes=120, resolution_minutes=480),
        SLAPolicy(name="Low SLA Policy", priority="Low", response_minutes=240, resolution_minutes=1440)
    ]
    db.add_all(policies)
    now = datetime.now(timezone.utc)
    tickets = [
        Ticket(ticket_code="INC-1001", subject="Production database server is down", description="Production database is not responding. Multiple employees cannot access the application.", priority="Critical", category="Database", asset_id=assets[0].id, status="Open", created_at=now - timedelta(minutes=100)),
        Ticket(ticket_code="INC-1002", subject="Application login failure", description="Users receive an authentication error while logging in.", priority="High", category="Application", asset_id=assets[1].id, status="Open", created_at=now - timedelta(minutes=90)),
        Ticket(ticket_code="INC-1003", subject="Laptop battery issue", description="Laptop battery drains quickly during normal use.", priority="Low", category="Hardware", asset_id=assets[2].id, status="Open", created_at=now - timedelta(minutes=60)),
        Ticket(
                ticket_code="INC-1004",
                subject="Production application is not responding",
                description="Users are experiencing timeouts and cannot access the production application.",
                priority="Critical",
                category="Application",
                asset_id=assets[1].id,
                status="Open",
                created_at=now - timedelta(minutes=5)
)
    ]
    db.add_all(tickets)
    incidents = [
        HistoricalIncident(incident_code="INC-0842", subject="Database service outage", description="Production database service stopped responding.", category="Database", asset_code="DB-SERVER-01", error_code="DB-500", root_cause="Database service stopped after disk space was exhausted.", resolution_steps="Check disk utilization, confirm database service status, free approved temporary space, and follow the database restart procedure."),
        HistoricalIncident(incident_code="INC-0761", subject="Database connection failure", description="Application could not connect to the database.", category="Database", asset_code="DB-SERVER-01", error_code="DB-CONN-01", root_cause="Database connection pool was exhausted.", resolution_steps="Check connection count, inspect application logs, and follow the documented connection-pool recovery procedure."),
        HistoricalIncident(incident_code="INC-0710", subject="Application authentication failure", description="Users could not log in.", category="Application", asset_code="APP-SERVER-02", error_code="AUTH-401", root_cause="Authentication service configuration expired.", resolution_steps="Verify authentication service health and follow the approved credential rotation procedure.")
    ]
    db.add_all(incidents)
    db.commit()

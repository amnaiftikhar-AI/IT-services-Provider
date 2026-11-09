from apscheduler.schedulers.background import BackgroundScheduler
from app.database import SessionLocal
from app.models import Ticket, SLAPolicy, RiskSnapshot
from app.services.sla_service import calculate_sla

scheduler = BackgroundScheduler()

def monitor_tickets():
    db = SessionLocal()
    try:
        tickets = db.query(Ticket).filter(Ticket.status.notin_(["Resolved", "Closed"])).all()
        for ticket in tickets:
            policy = db.query(SLAPolicy).filter(
                SLAPolicy.priority == ticket.priority,
                SLAPolicy.active.is_(True)
            ).order_by(SLAPolicy.version.desc()).first()
            if not policy:
                continue
            result = calculate_sla(ticket, policy)
            snapshot = RiskSnapshot(
                ticket_id=ticket.id,
                risk_level=result["risk_level"],
                response_remaining_minutes=result["response_remaining_minutes"],
                resolution_remaining_minutes=result["resolution_remaining_minutes"]
            )
            db.add(snapshot)
        db.commit()
    finally:
        db.close()

def start_scheduler(interval_minutes):
    if not scheduler.running:
        scheduler.add_job(
            monitor_tickets,
            "interval",
            minutes=interval_minutes,
            id="sla_monitor",
            replace_existing=True,
            max_instances=1
        )
        scheduler.start()

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()

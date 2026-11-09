import json
from app.ai.llm import ask_llm
from app.ai.prompts import SYSTEM_PROMPT
from app.schemas import InvestigationOut
from app.retrieval.hybrid_retriever import hybrid_search
from app.models import HistoricalIncident

def investigate_ticket(db, ticket, asset, sla_result):
    query = " ".join([
        ticket.ticket_code, ticket.subject, ticket.description, ticket.priority, ticket.category,
        asset.asset_code if asset else "",
        asset.asset_type if asset else "",
        asset.environment if asset else ""
    ])
    evidence = hybrid_search(db, query, top_k=10)
    incidents = db.query(HistoricalIncident).filter(
        HistoricalIncident.category.ilike(ticket.category)
    ).limit(10).all()
    incident_text = [
        {
            "incident_code": item.incident_code,
            "subject": item.subject,
            "description": item.description,
            "error_code": item.error_code,
            "root_cause": item.root_cause,
            "resolution_steps": item.resolution_steps
        } for item in incidents
    ]
    conflicts = []
    if asset:
        description = ticket.description.lower()
        if "staging" in description and asset.environment.lower() == "production":
            conflicts.append("Ticket description says staging, but asset record says production.")
        if "production" in description and asset.environment.lower() == "staging":
            conflicts.append("Ticket description says production, but asset record says staging.")
    context = {
        "ticket": {
            "ticket_code": ticket.ticket_code,
            "subject": ticket.subject,
            "description": ticket.description,
            "priority": ticket.priority,
            "category": ticket.category,
            "status": ticket.status
        },
        "asset": None if not asset else {
            "asset_code": asset.asset_code,
            "asset_type": asset.asset_type,
            "environment": asset.environment,
            "criticality": asset.criticality
        },
        "sla_calculated_by_python": sla_result,
        "retrieved_chunks": evidence,
        "historical_incidents": incident_text,
        "detected_conflicts": conflicts
    }
    raw = ask_llm(SYSTEM_PROMPT, json.dumps(context, default=str))
    try:
        parsed = json.loads(raw)
        parsed["sla"] = sla_result
        parsed["conflicts"] = list(set(parsed.get("conflicts", []) + conflicts))
        if not evidence and not incident_text:
            parsed["limitations"] = parsed.get("limitations", []) + ["No supporting knowledge-base evidence or matching historical incidents were found."]
        return InvestigationOut(**parsed).model_dump()
    except Exception:
        return {
            "risk_assessment": "The model did not return a valid structured report.",
            "sla": sla_result,
            "supporting_evidence": [],
            "similar_incidents": incident_text,
            "recommended_actions": [],
            "applicable_policies": [],
            "missing_information": [],
            "limitations": ["The AI response could not be validated. Please retry the investigation."],
            "conflicts": conflicts
        }

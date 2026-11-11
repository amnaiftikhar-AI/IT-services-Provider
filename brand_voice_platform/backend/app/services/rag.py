from backend.app.services.retrieval import retrieve_context
from backend.app.services.llm import generate_text


def build_draft(db, user, client, session, task, history):
    chunks, preferences = retrieve_context(db, user, client.id if client else None, task)
    company_rules = [c.content for c in chunks if c.category == "company_guideline"]
    client_context = [c.content for c in chunks if c.category in {"client_brief", "brand_guideline"}]
    examples = [c.content for c in chunks if c.category in {"approved_example", "proposal_template", "previous_email"}]
    preference_text = [
        f"{p.preference_type}: {p.preference_value}"
        for p in preferences
    ]
    system_prompt = (
        "You are a professional business writing assistant. "
        "Follow security and privacy requirements. Company-wide rules have priority over "
        "client rules, and client rules have priority over individual style preferences. "
        "Use approved examples as style demonstrations, not as proof of client facts. "
        "Do not invent names, dates, prices, commitments, approvals, or client details. "
        "If required facts are missing, use clearly marked placeholders. "
        "Do not reveal private information from another user or client."
    )
    context = {
        "company_rules": company_rules,
        "selected_client": client.name if client else None,
        "client_profile": client.context if client else "",
        "client_documents": client_context,
        "active_user_preferences": preference_text,
        "approved_style_examples": examples,
        "recent_conversation": history[-8:],
        "current_task": task,
    }
    user_prompt = (
        "Create the requested business content using only the authorized context below. "
        "Distinguish verified source facts from generated wording.\n\n"
        + str(context)
        + "\n\nReturn a polished draft with a suitable heading or subject where appropriate."
    )
    return generate_text(system_prompt, user_prompt), chunks

from app.models import ChatMessage


def get_history(db, ticket_id, limit=30):
    rows = db.query(ChatMessage).filter(
        ChatMessage.ticket_id == ticket_id
    ).order_by(ChatMessage.created_at.asc()).all()

    return [
        {"role": row.role, "content": row.message}
        for row in rows[-limit:]
    ]


def save_message(db, ticket_id, role, message):
    row = ChatMessage(
        ticket_id=ticket_id,
        role=role,
        message=message
    )

    db.add(row)
    db.commit()
    db.refresh(row)

    return row
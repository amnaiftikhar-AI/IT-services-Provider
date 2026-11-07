
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from amna_rag.models import AIConversation, AIMessage
from amna_rag.services.llm_service import (
    decompose_question,
    answer_from_context,
)
from amna_rag.services.retrieval_service import hybrid_search


# --------------------------------------------------
# 1. Detect greetings and simple conversational messages
# --------------------------------------------------

def is_small_talk(question: str) -> bool:
    greetings = {
        "hi",
        "hello",
        "hey",
        "hi there",
        "hello there",
        "hey there",
        "good morning",
        "good afternoon",
        "good evening",
        "how are you",
        "how are you doing",
        "what is up",
        "whats up",
        "thanks",
        "thank you",
        "thanks a lot",
        "bye",
        "goodbye",
        "see you",
    }

    normalized = re.sub(
        r"[^\w\s]",
        "",
        question.lower()
    ).strip()

    normalized = re.sub(r"\s+", " ", normalized)

    return normalized in greetings


# --------------------------------------------------
# 2. Get or create conversation
# --------------------------------------------------

def get_or_create_conversation(
    db: Session,
    user_id: str,
    conversation_key: str | None,
    ticket_id: int | None
):
    if conversation_key:
        conversation = (
            db.query(AIConversation)
            .filter_by(
                conversation_key=conversation_key,
                user_id=user_id,
                ticket_id=ticket_id
            )
            .first()
        )

        if conversation:
            return conversation

    key = str(uuid.uuid4())

    conversation = AIConversation(
        conversation_key=key,
        user_id=user_id,
        ticket_id=ticket_id,
        title="New investigation"
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


# --------------------------------------------------
# 3. Ask question
# --------------------------------------------------

def ask_question(
    db: Session,
    user_id: str,
    question: str,
    conversation_key: str | None = None,
    ticket_id: int | None = None
):
    question = question.strip()

    if not question:
        raise ValueError("Question cannot be empty.")

    # 1. Get or create conversation
    conversation = get_or_create_conversation(
        db,
        user_id,
        conversation_key,
        ticket_id
    )

    # 2. Load previous conversation messages
    history = [
        {
            "role": message.role,
            "content": message.content
        }
        for message in conversation.messages
    ]

    # 3. Initialize retrieval-related variables
    queries = []
    results = []
    sources = []

    # 4. Check whether the message is small talk
    if is_small_talk(question):

        # Do not execute the RAG retrieval pipeline
        answer = (
            "Hello! How can I help you today? "
            "If you have a specific IT issue "
            "(password reset, software request, backup, etc.), "
            "just let me know and I'll guide you through "
            "the next steps."
        )

        print("\n========== SMALL TALK ==========")
        print("Question:", question)
        print("Knowledge-base retrieval: SKIPPED")
        print("Sources: None")
        print("================================\n")

    else:

        # 5. Decompose the user's IT question
        queries = decompose_question(question)

        # Ensure the original question is always searched
        queries = list(dict.fromkeys(
            [question] + [
                q.strip() for q in queries
                if q and q.strip()
            ]
        ))

        # 6. Perform hybrid retrieval for each query
        results_by_chunk = {}

        for query in queries:

            retrieved_items = hybrid_search(
                db,
                query,
                dense_k=8,
                bm25_k=8,
                final_k=6
            )

            for item in retrieved_items:

                meta = item["metadata"]

                key = (
                    meta.get("chunk_id"),
                    item["content"][:100]
                )

                if key not in results_by_chunk:

                    results_by_chunk[key] = item.copy()

                else:

                    # Accumulate RRF scores when the same
                    # chunk is retrieved by multiple queries
                    results_by_chunk[key]["rrf"] += item["rrf"]

        # 7. Rank chunks and select the top six
        results = sorted(
            results_by_chunk.values(),
            key=lambda item: item["rrf"],
            reverse=True
        )[:6]

        # 8. Debug retrieval results
        print("\n========== RETRIEVAL DEBUG ==========")
        print("Original question:", question)
        print("Decomposed queries:", queries)

        for item in results:

            meta = item["metadata"]

            print("\nDocument:", (
                meta.get("source")
                or meta.get("filename")
                or "Unknown document"
            ))

            print("Section:", meta.get("section"))
            print("Page:", meta.get("page"))
            print("RRF score:", item["rrf"])
            print("Dense rank:", item.get("dense_rank"))
            print("BM25 rank:", item.get("bm25_rank"))
            print("Content:", item["content"][:250])

        print("=====================================\n")

        # 9. Prepare LLM context and unique source references
        context_parts = []
        seen_sources = set()

        for item in results:

            meta = item["metadata"]

            source = {
                "document": (
                    meta.get("source")
                    or meta.get("filename")
                    or "Unknown document"
                ),
                "page": meta.get("page"),
                "section": meta.get("section"),
                "chunk_id": meta.get("chunk_id"),
                "score": round(item["rrf"], 5)
            }

            # Avoid duplicate document/page/section references
            source_key = (
                source["document"],
                source["page"],
                source["section"]
            )

            if source_key not in seen_sources:
                seen_sources.add(source_key)
                sources.append(source)

            # Include every selected chunk in LLM context
            context_parts.append(
                f"[Source: {source['document']}; "
                f"page: {source['page']}; "
                f"section: {source['section']}]\n"
                f"{item['content']}"
            )

        # 10. Generate the AI answer
        context = "\n\n---\n\n".join(context_parts)

        answer = answer_from_context(
            question,
            context,
            history
        )

    # 11. Update conversation title
    if (
        conversation.title == "New investigation"
        and not is_small_talk(question)
    ):
        conversation.title = question[:240]

    # 12. Save user message
    db.add(
        AIMessage(
            conversation_id=conversation.id,
            role="user",
            content=question
        )
    )

    # 13. Save assistant answer and source references
    db.add(
        AIMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            sources_json=sources
        )
    )

    conversation.updated_at = datetime.now(timezone.utc)

    db.commit()

    # 14. Return API response
    return {
        "conversation_key": conversation.conversation_key,
        "answer": answer,
        "sources": sources,
        "decomposed_queries": queries
    }


# --------------------------------------------------
# 4. Conversation history
# --------------------------------------------------

def conversation_history(
    db: Session,
    user_id: str,
    role: str
):
    query = db.query(AIConversation)

    if role != "admin":
        query = query.filter_by(user_id=user_id)

    return query.order_by(
        AIConversation.updated_at.desc()
    ).all()


# --------------------------------------------------
# 5. AI ticket assistance
# --------------------------------------------------

def ticket_assistance(
    db: Session,
    user_id: str,
    payload
):
    question = (
        f"Investigate ticket #{payload.ticket_id}. "
        f"Subject: {payload.subject}. "
        f"Description: {payload.description}. "
        f"Category: {payload.category}. "
        f"Priority: {payload.priority}. "
        f"Asset: {payload.asset or 'Not provided'}. "
        "Provide a concise summary, safe troubleshooting steps, "
        "missing information, and whether senior escalation is justified."
    )

    result = ask_question(
        db,
        user_id,
        question,
        ticket_id=payload.ticket_id
    )

    # Extract suggested troubleshooting steps
    steps = [
        line.strip(" -*0123456789.\t")
        for line in result["answer"].splitlines()
        if line.strip()
        and (
            line.strip()[0].isdigit()
            or line.strip().startswith(("-", "*"))
        )
    ]

    # Identify missing information
    missing = []

    low_answer = result["answer"].lower()

    if (
        "not enough information" in low_answer
        or "cannot determine" in low_answer
        or "insufficient" in low_answer
    ):
        missing.append(
            "Collect the exact error message, affected device, "
            "and steps already attempted."
        )

    return {
        "ticket_id": payload.ticket_id,
        "issue_summary": result["answer"].splitlines()[0][:500],
        "troubleshooting_steps": steps or [result["answer"]],
        "sources": result["sources"],
        "missing_information": missing,
        "escalation_recommended": bool(missing),
        "escalation_reason": (
            "Available documentation is insufficient; "
            "collect missing details or escalate to a senior agent."
            if missing
            else "No escalation is indicated by the retrieved evidence; "
                 "agent should use judgement."
        )
    }

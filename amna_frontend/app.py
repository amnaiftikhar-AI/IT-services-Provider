
import streamlit as st
from datetime import datetime

from amna_frontend.api_client import request


# ==================================================
# 1. PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="IT Knowledge Hub",
    page_icon="🧠",
    layout="wide"
)


# ==================================================
# 2. CUSTOM CSS AND HEADER
# ==================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    .block-container {
        padding-top: 1.8rem;
        max-width: 1450px;
    }

    .hero {
        padding: 28px 30px;
        border-radius: 18px;
        background: linear-gradient(120deg, #102a43, #176b87);
        color: white;
        margin-bottom: 20px;
    }

    .hero h1 {
        font-family: 'Manrope', sans-serif;
        font-size: 2rem;
        margin: 0 0 8px 0;
        color: white;
    }

    .hero p {
        color: #d9edf5;
        margin: 0;
    }

    .metric {
        background: #f3f7fb;
        border: 1px solid #e2eaf2;
        border-radius: 14px;
        padding: 16px;
    }

    .metric small {
        color: #526477;
    }

    .source {
        background: #f7fafc;
        border-left: 4px solid #1d829b;
        padding: 12px 14px;
        border-radius: 8px;
        margin: 8px 0;
    }

    div.stButton > button {
        border-radius: 9px;
        font-weight: 600;
    }
    </style>

    <div class="hero">
        <h1>IT Knowledge Hub</h1>
        <p>
            Search technical knowledge, manage documentation
            and investigate IT issues with grounded AI.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)


# ==================================================
# 3. SIDEBAR SETTINGS
# ==================================================

with st.sidebar:

    st.markdown("### Workspace settings")

    st.session_state.api_url = st.text_input(
        "FastAPI URL",
        st.session_state.get(
            "api_url",
            "http://127.0.0.1:8000"
        )
    )

    st.text_input(
        "Huda JWT token (recommended)",
        key="jwt_token",
        type="password",
        help="Paste a token issued by Huda's authentication module."
    )

    st.session_state.user_id = st.text_input(
        "User ID (local development only)",
        st.session_state.get("user_id", "amna-demo")
    )

    st.session_state.user_role = st.selectbox(
        "Local role",
        ["admin", "support_agent", "employee"],
        index=0,
        help="Development headers work only when ALLOW_DEV_AUTH=true."
    )

    st.caption(
        "Production: use Huda's JWT. "
        "Do not rely on development headers."
    )


# ==================================================
# 4. LOAD KNOWLEDGE DOCUMENTS AND METRICS
# ==================================================

try:
    docs = request(
        "GET",
        "/api/knowledge/documents"
    ) or []

except Exception as exc:
    docs = []
    st.warning(f"Could not load knowledge documents: {exc}")


chunks = sum(
    doc.get("chunk_count", 0)
    for doc in docs
)

pdf_count = sum(
    doc.get("file_type") == "pdf"
    for doc in docs
)

txt_count = sum(
    doc.get("file_type") == "txt"
    for doc in docs
)


cols = st.columns(4)

metrics = [
    (len(docs), "Documents"),
    (chunks, "Searchable chunks"),
    (pdf_count, "PDF files"),
    (txt_count, "TXT files")
]

for col, (value, label) in zip(cols, metrics):

    col.markdown(
        f"""
        <div class="metric">
            <small>{label}</small>
            <h2>{value}</h2>
        </div>
        """,
        unsafe_allow_html=True
    )


# ==================================================
# 5. APPLICATION TABS
# ==================================================

pages = st.tabs(
    [
        "💬 AI Assistant",
        "📚 Knowledge Documents",
        "🔎 Hybrid Search",
        "🎫 Ticket Copilot",
        "🕘 Conversation History"
    ]
)


# ==================================================
# 6. AI ASSISTANT
# ==================================================

with pages[0]:

    st.subheader("Ask the IT Knowledge Assistant")

    st.caption(
        "Answers are grounded in your uploaded documents. "
        "Relevant sources are displayed below each answer."
    )

    # Initialize conversation state
    if "conversation_key" not in st.session_state:
        st.session_state.conversation_key = None

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # Display previous messages
    for msg in st.session_state.chat_messages:

        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            # Display saved sources when available
            sources = msg.get("sources") or []

            if sources:
                st.markdown("**Retrieved supporting sources**")

                for source in sources:
                    st.markdown(
                        f"""
                        <div class="source">
                            <b>{source.get('document', 'Unknown document')}</b>
                            · Page {source.get('page') or 'N/A'}
                            · {source.get('section') or 'General'}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

    # Chat input
    question = st.chat_input(
        "Example: My VPN is connected but internal apps do not open..."
    )

    if question:

        # Save and display user message
        st.session_state.chat_messages.append(
            {
                "role": "user",
                "content": question
            }
        )

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):

            with st.spinner("Preparing your answer..."):

                try:

                    data = request(
                        "POST",
                        "/api/ai/chat",
                        json={
                            "question": question,
                            "conversation_key": (
                                st.session_state.conversation_key
                            )
                        }
                    )

                except Exception as exc:
                    data = None
                    st.error(f"Could not get an AI response: {exc}")

            if data:

                # Update conversation key
                st.session_state.conversation_key = (
                    data["conversation_key"]
                )

                # Display AI answer
                answer = data.get(
                    "answer",
                    "No answer was returned."
                )

                st.markdown(answer)

                # Display sources only when available
                sources = data.get("sources") or []

                if sources:

                    st.markdown(
                        "**Retrieved supporting sources**"
                    )

                    for source in sources:

                        st.markdown(
                            f"""
                            <div class="source">
                                <b>
                                    {source.get('document', 'Unknown document')}
                                </b>
                                · Page {source.get('page') or 'N/A'}
                                · {source.get('section') or 'General'}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                # Save assistant message and its sources
                st.session_state.chat_messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sources": sources
                    }
                )

                # Display search queries only when available
                queries = data.get("decomposed_queries") or []

                if queries:

                    with st.expander("Search queries used"):

                        for query in queries:
                            st.write(f"- {query}")

            else:
                st.error(
                    "The assistant could not process your request. "
                    "Please check the FastAPI server and try again."
                )

    # Start new conversation
    if st.button("Start new conversation"):

        st.session_state.conversation_key = None
        st.session_state.chat_messages = []

        st.rerun()


# ==================================================
# 7. KNOWLEDGE DOCUMENTS
# ==================================================

with pages[1]:

    st.subheader("Manage knowledge documents")

    st.write(
        "Upload PDF/TXT files. Documents are extracted, "
        "split, stored in PostgreSQL and indexed in FAISS."
    )

    # Upload form
    with st.form("upload_form"):

        files = st.file_uploader(
            "Choose technical documents",
            type=["pdf", "txt"],
            accept_multiple_files=True
        )

        c1, c2, c3 = st.columns(3)

        document_type = c1.selectbox(
            "Document type",
            [
                "Technical Guide",
                "Troubleshooting",
                "IT Policy",
                "Error Reference",
                "Resolved Ticket Summary"
            ]
        )

        department = c2.selectbox(
            "Department",
            [
                "IT",
                "HR",
                "Finance",
                "Operations",
                "All Departments"
            ]
        )

        system_name = c3.text_input(
            "System / device",
            "General IT"
        )

        submitted = st.form_submit_button(
            "Upload and index documents",
            type="primary"
        )

    if submitted:

        if not files:

            st.warning(
                "Select at least one PDF or TXT file."
            )

        else:

            upload_files = [
                (
                    "files",
                    (
                        file.name,
                        file.getvalue(),
                        file.type or "application/octet-stream"
                    )
                )
                for file in files
            ]

            try:

                result = request(
                    "POST",
                    "/api/knowledge/upload",
                    files=upload_files,
                    data={
                        "document_type": document_type,
                        "department": department,
                        "system_name": system_name
                    }
                )

                if result:
                    st.success(result)

            except Exception as exc:
                st.error(f"Upload failed: {exc}")

    # Uploaded document list
    st.markdown("#### Uploaded documents")

    try:

        docs = request(
            "GET",
            "/api/knowledge/documents"
        ) or []

    except Exception as exc:

        docs = []
        st.error(f"Could not load documents: {exc}")

    if docs:

        for doc in docs:

            with st.container(border=True):

                c1, c2, c3, c4 = st.columns([4, 2, 2, 1])

                c1.markdown(f"**{doc['filename']}**")

                c1.caption(
                    f"{doc['document_type']} · "
                    f"{doc['department']} · "
                    f"{doc['system_name']}"
                )

                c2.write(
                    f"{doc['chunk_count']} chunks"
                )

                c3.write(
                    "✅ Indexed"
                    if doc["is_indexed"]
                    else "⏳ Not indexed"
                )

                # Delete document
                if c4.button(
                    "Delete",
                    key=f"delete_{doc['id']}"
                ):

                    try:

                        result = request(
                            "DELETE",
                            f"/api/knowledge/documents/{doc['id']}"
                        )

                        if result:
                            st.success(result["message"])
                            st.rerun()

                    except Exception as exc:
                        st.error(f"Delete failed: {exc}")

                # Replace document
                with st.expander(
                    f"Update {doc['filename']}"
                ):

                    replacement = st.file_uploader(
                        "Choose replacement PDF/TXT",
                        type=["pdf", "txt"],
                        key=f"replace_file_{doc['id']}"
                    )

                    u1, u2, u3 = st.columns(3)

                    new_type = u1.text_input(
                        "Document type",
                        doc["document_type"],
                        key=f"replace_type_{doc['id']}"
                    )

                    new_department = u2.text_input(
                        "Department",
                        doc["department"],
                        key=f"replace_dept_{doc['id']}"
                    )

                    new_system = u3.text_input(
                        "System / device",
                        doc["system_name"],
                        key=f"replace_system_{doc['id']}"
                    )

                    if st.button(
                        "Save replacement and re-index",
                        key=f"replace_{doc['id']}"
                    ):

                        if not replacement:

                            st.warning(
                                "Choose a replacement file first."
                            )

                        else:

                            try:

                                result = request(
                                    "PUT",
                                    f"/api/knowledge/documents/{doc['id']}",
                                    files={
                                        "file": (
                                            replacement.name,
                                            replacement.getvalue(),
                                            replacement.type
                                            or "application/octet-stream"
                                        )
                                    },
                                    data={
                                        "document_type": new_type,
                                        "department": new_department,
                                        "system_name": new_system
                                    }
                                )

                                if result:
                                    st.success(
                                        result.get(
                                            "message",
                                            "Document updated."
                                        )
                                    )
                                    st.rerun()

                            except Exception as exc:
                                st.error(
                                    f"Document update failed: {exc}"
                                )

    else:

        st.info(
            "No documents found. Upload the supplied sample knowledge base first."
        )

    # Rebuild FAISS index
    if st.button("Rebuild FAISS index"):

        try:

            result = request(
                "POST",
                "/api/knowledge/reindex"
            )

            if result:
                st.success(
                    f"Indexed {result['chunks_indexed']} chunks."
                )

        except Exception as exc:
            st.error(f"Index rebuilding failed: {exc}")


# ==================================================
# 8. HYBRID SEARCH
# ==================================================

with pages[2]:

    st.subheader("Hybrid document search")

    q = st.text_input(
        "Search exact error codes, device names or describe an issue"
    )

    f1, f2 = st.columns(2)

    type_filter = f1.selectbox(
        "Filter document type",
        [
            "All",
            "Technical Guide",
            "Troubleshooting",
            "IT Policy",
            "Error Reference",
            "Resolved Ticket Summary"
        ]
    )

    dept_filter = f2.selectbox(
        "Filter department",
        [
            "All",
            "IT",
            "HR",
            "Finance",
            "Operations",
            "All Departments"
        ]
    )

    if st.button(
        "Search knowledge base",
        type="primary"
    ) and q:

        search_payload = {
            "question": q,
            "dense_k": 8,
            "bm25_k": 8,
            "final_k": 6
        }

        if type_filter != "All":
            search_payload["document_type"] = type_filter

        if dept_filter != "All":
            search_payload["department"] = dept_filter

        try:

            result = request(
                "POST",
                "/api/knowledge/search",
                json=search_payload
            ) or []

            for i, item in enumerate(result, 1):

                meta = item["metadata"]

                with st.container(border=True):

                    st.markdown(
                        f"""
                        **{i}. {
                            meta.get('source')
                            or meta.get('filename')
                            or 'Document'
                        }**
                        · {meta.get('section') or 'General'}
                        · Page {meta.get('page') or 'N/A'}
                        """
                    )

                    st.write(item["content"])

                    st.caption(
                        f"RRF score: {item['rrf_score']:.5f}"
                    )

            if not result:

                st.info(
                    "No matching knowledge chunks were found."
                )

        except Exception as exc:
            st.error(f"Search failed: {exc}")


# ==================================================
# 9. TICKET COPILOT
# ==================================================

with pages[3]:

    st.subheader("AI-assisted ticket investigation")

    st.caption(
        "This creates suggestions only. It never changes "
        "Huda's ticket status, assignment or resolution."
    )

    with st.form("ticket_form"):

        ticket_id = st.number_input(
            "Ticket ID",
            min_value=1,
            step=1
        )

        subject = st.text_input("Subject")

        description = st.text_area(
            "Description",
            height=120
        )

        a, b = st.columns(2)

        category = a.text_input(
            "Category",
            "Network"
        )

        priority = b.selectbox(
            "Priority",
            ["Low", "Medium", "High", "Critical"],
            index=1
        )

        asset = st.text_input(
            "Asset details (optional)"
        )

        go = st.form_submit_button(
            "Investigate ticket",
            type="primary"
        )

    if go:

        try:

            result = request(
                "POST",
                "/api/ai/ticket-assistance",
                json={
                    "ticket_id": int(ticket_id),
                    "subject": subject,
                    "description": description,
                    "category": category,
                    "priority": priority,
                    "asset": (
                        {"description": asset}
                        if asset
                        else None
                    )
                }
            )

            if result:

                st.markdown("### Issue summary")

                st.write(
                    result["issue_summary"]
                )

                st.markdown("### Suggested troubleshooting")

                for step in result["troubleshooting_steps"]:
                    st.markdown(f"- {step}")

                st.markdown("### Missing information")

                st.write(
                    result["missing_information"]
                    or "No specific missing information identified."
                )

                st.markdown("### Escalation")

                st.write(
                    result["escalation_reason"]
                )

                # Display ticket sources only when available
                sources = result.get("sources") or []

                if sources:

                    st.markdown("### Sources")

                    for source in sources:

                        st.write(
                            f"{source.get('document', 'Unknown document')} "
                            f"· Page {source.get('page') or 'N/A'} "
                            f"· {source.get('section') or 'General'}"
                        )

        except Exception as exc:
            st.error(
                f"Ticket investigation failed: {exc}"
            )


# ==================================================
# 10. CONVERSATION HISTORY
# ==================================================

with pages[4]:

    st.subheader("Saved conversations")

    if st.button("Refresh history"):
        st.rerun()

    try:

        conversations = request(
            "GET",
            "/api/ai/conversations"
        ) or []

    except Exception as exc:

        conversations = []
        st.error(f"Could not load conversation history: {exc}")

    if not conversations:

        st.info("No saved conversations yet.")

    for conversation in conversations:

        with st.expander(
            f"{conversation['title']} · "
            f"Ticket: {conversation['ticket_id'] or 'General'}"
        ):

            left, right = st.columns([5, 1])

            # Load conversation
            if left.button(
                "Load this conversation",
                key=f"load_{conversation['conversation_key']}"
            ):

                st.session_state.conversation_key = (
                    conversation["conversation_key"]
                )

                st.session_state.chat_messages = [
                    {
                        "role": message["role"],
                        "content": message["content"],
                        "sources": message.get("sources") or []
                    }
                    for message in conversation["messages"]
                ]

                st.success(
                    "Conversation loaded. Open the AI Assistant tab to continue."
                )

            # Delete conversation
            if right.button(
                "Delete",
                key=f"delete_convo_{conversation['conversation_key']}"
            ):

                try:

                    result = request(
                        "DELETE",
                        f"/api/ai/conversations/{conversation['conversation_key']}"
                    )

                    if result:
                        st.success(result["message"])
                        st.rerun()

                except Exception as exc:
                    st.error(
                        f"Conversation deletion failed: {exc}"
                    )

            # Display conversation messages
            for message in conversation["messages"]:

                st.markdown(
                    f"**{message['role'].title()}**"
                )

                st.write(message["content"])

                # Display only available sources
                sources = message.get("sources") or []

                if sources:

                    for source in sources:

                        st.caption(
                            f"Source: "
                            f"{source.get('document', 'Unknown document')} "
                            f"· Page {source.get('page') or 'N/A'}"
                        )

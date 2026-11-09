import streamlit as st
import requests
import os

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="SLA Investigation Assistant", layout="wide")
st.title("AI-Powered SLA Investigation Assistant")

page = st.sidebar.selectbox(
    "Choose a page",
    ["Dashboard", "Tickets", "Investigate Ticket", "Ticket Chat", "Knowledge Base"]
)

def get_data(path):
    response = requests.get(f"{API_URL}{path}", timeout=60)
    response.raise_for_status()
    return response.json()

if page == "Dashboard":
    st.subheader("SLA Risk Dashboard")
    try:
        rows = get_data("/admin/risks")
        st.metric("Active tickets", len(rows))
        st.dataframe(rows, width='content')
    except Exception as error:
        st.error(str(error))

elif page == "Tickets":
    st.subheader("Support Tickets")
    try:
        st.dataframe(get_data("/tickets/"), width='content')
    except Exception as error:
        st.error(str(error))

elif page == "Investigate Ticket":
    st.subheader("Investigate a Ticket")
    ticket_code = st.text_input("Ticket ID", "INC-1001")
    if st.button("Investigate"):
        try:
            response = requests.post(f"{API_URL}/investigations/{ticket_code}", timeout=180)
            response.raise_for_status()
            st.session_state["last_report"] = response.json()["report"]
        except Exception as error:
            st.error(str(error))
    if "last_report" in st.session_state:
        st.json(st.session_state["last_report"])

elif page == "Ticket Chat":
    st.subheader("Ticket-specific Follow-up Chat")
    ticket_code = st.text_input("Ticket ID", "INC-1001", key="chat_ticket")
    try:
        history = get_data(f"/chat/{ticket_code}/history")
        for message in history["messages"]:
            with st.chat_message(message["role"]):
                st.write(message["content"])
    except Exception:
        pass
    question = st.chat_input("Ask a question about this ticket")
    if question:
        try:
            response = requests.post(
                f"{API_URL}/chat/{ticket_code}",
                json={"question": question},
                timeout=180
            )
            response.raise_for_status()
            st.rerun()
        except Exception as error:
            st.error(str(error))

elif page == "Knowledge Base":
    st.subheader("Upload SLA Policies and Incident Documents")
    uploaded = st.file_uploader("Upload PDF or TXT", type=["pdf", "txt"])
    document_type = st.selectbox("Document type", ["sla_policy", "escalation", "historical_incident", "general"])
    if uploaded and st.button("Upload and Index"):
        try:
            response = requests.post(
                f"{API_URL}/documents/upload",
                files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
                data={"document_type": document_type},
                timeout=300
            )
            response.raise_for_status()
            st.success(response.json())
        except Exception as error:
            st.error(str(error))
    try:
        st.dataframe(get_data("/documents/"), width='content')
    except Exception as error:
        st.error(str(error))

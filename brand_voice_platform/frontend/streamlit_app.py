import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Brand Voice AI", page_icon="✍️", layout="wide")
st.title("Personalized Brand Voice & Content Intelligence")

if "token" not in st.session_state:
    st.session_state.token = ""
if "draft_id" not in st.session_state:
    st.session_state.draft_id = None
if "draft" not in st.session_state:
    st.session_state.draft = ""

def headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}

def api_error(response):
    try:
        detail = response.json().get("detail", response.text)
    except Exception:
        detail = response.text
    st.error(str(detail))

with st.sidebar:
    st.subheader("Account")
    mode = st.radio("Choose", ["Login", "Register"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button(mode):
        endpoint = "/auth/login" if mode == "Login" else "/auth/register"
        response = requests.post(
            API_URL + endpoint,
            json={"email": email, "password": password},
            timeout=30,
        )
        if response.ok:
            st.session_state.token = response.json()["access_token"]
            st.success("Authenticated")
        else:
            api_error(response)
    if st.session_state.token and st.button("Logout"):
        st.session_state.token = ""
        st.rerun()

if not st.session_state.token:
    st.info("Log in or register to use the writing platform.")
    st.stop()

tabs = st.tabs(["Clients", "Upload Documents", "Writing", "Preferences"])

with tabs[0]:
    st.subheader("Client profiles")
    with st.form("client_form"):
        client_name = st.text_input("Client name")
        client_context = st.text_area("Client context")
        create_client = st.form_submit_button("Create client")
    if create_client:
        response = requests.post(
            API_URL + "/clients",
            headers=headers(),
            json={"name": client_name, "context": client_context},
            timeout=30,
        )
        if response.ok:
            st.success(f"Client created: {response.json()['id']}")
        else:
            api_error(response)
    response = requests.get(API_URL + "/clients", headers=headers(), timeout=30)
    if response.ok:
        st.dataframe(response.json(), use_container_width=True)

with tabs[1]:
    st.subheader("Upload PDF or TXT")
    clients_response = requests.get(API_URL + "/clients", headers=headers(), timeout=30)
    clients = clients_response.json() if clients_response.ok else []
    client_options = {"No client": None}
    client_options.update({f"{c['name']} (ID {c['id']})": c["id"] for c in clients})
    selected_client_label = st.selectbox("Client", list(client_options.keys()))
    category = st.selectbox(
        "Document category",
        [
            "brand_guideline",
            "proposal_template",
            "previous_email",
            "approved_example",
            "rejected_example",
            "client_brief",
            "company_guideline",
            "other",
        ],
    )
    uploaded = st.file_uploader("Choose a PDF or TXT file", type=["pdf", "txt"])
    if st.button("Upload and process", disabled=uploaded is None):
        response = requests.post(
            API_URL + "/documents/upload",
            headers=headers(),
            data={"category": category, "client_id": client_options[selected_client_label] or ""},
            files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
            timeout=180,
        )
        if response.ok:
            st.success(response.json())
        else:
            api_error(response)
    docs_response = requests.get(API_URL + "/documents", headers=headers(), timeout=30)
    if docs_response.ok:
        st.dataframe(docs_response.json(), use_container_width=True)

with tabs[2]:
    st.subheader("Writing workspace")
    clients_response = requests.get(API_URL + "/clients", headers=headers(), timeout=30)
    clients = clients_response.json() if clients_response.ok else []
    client_options = {"No client": None}
    client_options.update({f"{c['name']} (ID {c['id']})": c["id"] for c in clients})
    selected_label = st.selectbox("Select client", list(client_options.keys()), key="write_client")
    if st.button("Create writing session"):
        response = requests.post(
            API_URL + "/sessions",
            headers=headers(),
            json={"title": "New writing session", "client_id": client_options[selected_label]},
            timeout=30,
        )
        if response.ok:
            st.session_state.session_id = response.json()["id"]
            st.success(f"Session created: {st.session_state.session_id}")
        else:
            api_error(response)
    sessions_response = requests.get(API_URL + "/sessions", headers=headers(), timeout=30)
    sessions = sessions_response.json() if sessions_response.ok else []
    if sessions:
        session_map = {f"{s['title']} (ID {s['id']})": s["id"] for s in sessions}
        chosen_session = st.selectbox("Select session", list(session_map.keys()))
        if st.button("Resume selected session"):
            response = requests.post(
                API_URL + f"/sessions/{session_map[chosen_session]}/resume",
                headers=headers(),
                timeout=30,
            )
            if response.ok:
                st.session_state.session_id = session_map[chosen_session]
                st.success("Session resumed")
            else:
                api_error(response)
    task = st.text_area("What would you like to write?", height=120)
    if st.button("Generate draft"):
        if not st.session_state.get("session_id"):
            st.warning("Create or resume a session first.")
        elif not task.strip():
            st.warning("Enter a writing task.")
        else:
            response = requests.post(
                API_URL + "/drafts/generate",
                headers=headers(),
                json={
                    "session_id": st.session_state.session_id,
                    "client_id": client_options[selected_label],
                    "task": task,
                },
                timeout=180,
            )
            if response.ok:
                result = response.json()
                st.session_state.draft_id = result["draft_id"]
                st.session_state.draft = result["draft"]
                st.success(f"Draft generated. Retrieved chunks: {result['retrieved_chunks']}")
            else:
                api_error(response)
    if st.session_state.draft_id:
        edited = st.text_area("Edit your draft", value=st.session_state.draft, height=260, key=f"draft_{st.session_state.draft_id}")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Save revision"):
                response = requests.post(
                    API_URL + f"/drafts/{st.session_state.draft_id}/revise",
                    headers=headers(),
                    json={"final_text": edited},
                    timeout=120,
                )
                if response.ok:
                    st.success(response.json())
                else:
                    api_error(response)
        with col2:
            if st.button("Approve"):
                response = requests.post(
                    API_URL + f"/drafts/{st.session_state.draft_id}/feedback",
                    headers=headers(),
                    json={"action": "approved", "rating": 5},
                    timeout=30,
                )
                if response.ok:
                    st.success("Draft approved")
                else:
                    api_error(response)
        with col3:
            if st.button("Reject"):
                response = requests.post(
                    API_URL + f"/drafts/{st.session_state.draft_id}/feedback",
                    headers=headers(),
                    json={"action": "rejected", "rating": 1},
                    timeout=30,
                )
                if response.ok:
                    st.success("Draft rejected")
                else:
                    api_error(response)

with tabs[3]:
    st.subheader("Learned preferences")
    response = requests.get(API_URL + "/preferences", headers=headers(), timeout=30)
    if response.ok:
        preferences = response.json()
        st.dataframe(preferences, use_container_width=True)
        for preference in preferences:
            with st.expander(f"{preference['type']}: {preference['value']}"):
                status = st.selectbox(
                    "Status",
                    ["candidate", "active", "inactive"],
                    index=["candidate", "active", "inactive"].index(preference["status"]),
                    key=f"pref_{preference['id']}",
                )
                if st.button("Update preference", key=f"update_{preference['id']}"):
                    result = requests.patch(
                        API_URL + f"/preferences/{preference['id']}",
                        headers=headers(),
                        json={"status": status},
                        timeout=30,
                    )
                    if result.ok:
                        st.success("Preference updated")
                        st.rerun()
                    else:
                        api_error(result)
                if st.button("Delete preference", key=f"delete_{preference['id']}"):
                    result = requests.delete(
                        API_URL + f"/preferences/{preference['id']}",
                        headers=headers(),
                        timeout=30,
                    )
                    if result.ok:
                        st.success("Preference deleted")
                        st.rerun()
                    else:
                        api_error(result)

import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="IT Service Desk", layout="wide")
st.title("IT Service Desk")

if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None

def headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}

def api_get(path):
    response = requests.get(API_URL + path, headers=headers(), timeout=20)
    if response.status_code >= 400:
        st.error(response.text)
        return None
    return response.json()

def api_post(path, data):
    response = requests.post(API_URL + path, json=data, headers=headers(), timeout=20)
    if response.status_code >= 400:
        st.error(response.text)
        return None
    return response.json()

def api_patch(path, data=None):
    response = requests.patch(API_URL + path, json=data, headers=headers(), timeout=20)
    if response.status_code >= 400:
        st.error(response.text)
        return None
    return response.json()

def api_put(path, data):
    response = requests.put(API_URL + path, json=data, headers=headers(), timeout=20)
    if response.status_code >= 400:
        st.error(response.text)
        return None
    return response.json()

def login_page():
    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            response = requests.post(API_URL + "/auth/login", data={"username": email, "password": password})
            if response.status_code == 200:
                st.session_state.token = response.json()["access_token"]
                me_response = requests.get(API_URL + "/auth/me", headers=headers())
                st.session_state.user = me_response.json()
                st.rerun()
            else:
                st.error(response.text)
    with tab2:
        name = st.text_input("Full name", key="reg_name")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_password")
        role = st.selectbox("Role", ["employee", "support_agent"])
        department = st.text_input("Department")
        teams = requests.get(API_URL + "/support-teams")
        team_data = teams.json() if teams.status_code == 200 else []
        team_map = {t["name"]: t["id"] for t in team_data}
        team_name = st.selectbox("Support team (for agents)", ["None"] + list(team_map.keys()))
        if st.button("Register"):
            payload = {"name": name, "email": reg_email, "password": reg_password, "role": role, "department": department or None, "support_team_id": team_map.get(team_name)}
            response = requests.post(API_URL + "/auth/register", json=payload)
            if response.status_code == 200:
                st.success("Account created. Please log in.")
            else:
                st.error(response.text)

def show_tickets():
    tickets = api_get("/tickets")
    if tickets is None:
        return
    if tickets:
        st.dataframe(tickets, use_container_width=True)
    else:
        st.info("No tickets found.")
    return tickets

def employee_page():
    st.header("Employee Dashboard")
    with st.expander("Create a ticket", expanded=True):
        subject = st.text_input("Subject")
        description = st.text_area("Description")
        category = st.selectbox("Category", ["Hardware", "Network", "Software", "Accounts", "Other"])
        priority = st.selectbox("Priority", ["Critical", "High", "Medium", "Low"])
        assets = api_get("/assets") or []
        asset_options = {"No asset": None}
        asset_options.update({f'{a["asset_name"]} (ID {a["id"]})': a["id"] for a in assets if a["status"] == "Active"})
        asset_choice = st.selectbox("Related asset", list(asset_options.keys()))
        if st.button("Submit ticket"):
            result = api_post("/tickets", {"subject": subject, "description": description, "category": category, "priority": priority, "asset_id": asset_options[asset_choice]})
            if result:
                st.success(f'Ticket created: {result["ticket_number"]}')
                st.rerun()
    st.subheader("My tickets")
    tickets = show_tickets() or []
    if tickets:
        selected = st.selectbox("Select ticket", tickets, format_func=lambda x: f'{x["ticket_number"]} - {x["subject"]}')
        if selected:
            st.write(selected)
            comments = api_get(f'/tickets/{selected["id"]}/comments') or []
            st.write("Comments")
            st.dataframe(comments, use_container_width=True)
            comment = st.text_area("Add follow-up comment", key="employee_comment")
            if st.button("Send comment"):
                if api_post(f'/tickets/{selected["id"]}/comments', {"content": comment, "is_internal": False}):
                    st.success("Comment added")
                    st.rerun()
            if selected["status"] == "Resolved":
                col1, col2 = st.columns(2)
                if col1.button("Confirm resolution"):
                    if api_patch(f'/tickets/{selected["id"]}/confirm'):
                        st.success("Ticket closed")
                        st.rerun()
                if col2.button("Reopen ticket"):
                    if api_patch(f'/tickets/{selected["id"]}/reopen'):
                        st.success("Ticket reopened")
                        st.rerun()

def agent_page():
    st.header("Support Agent Dashboard")
    tickets = show_tickets() or []
    if not tickets:
        return
    selected = st.selectbox("Select ticket", tickets, format_func=lambda x: f'{x["ticket_number"]} - {x["subject"]}')
    if selected:
        st.subheader("Ticket details")
        st.json(selected)
        agents = requests.get(API_URL + "/users/managers", headers=headers())
        agent_list = agents.json() if agents.status_code == 200 else []
        agent_map = {f'{a["name"]} (ID {a["id"]})': a["id"] for a in agent_list}
        if agent_map:
            chosen = st.selectbox("Assign to", list(agent_map.keys()))
            if st.button("Assign ticket"):
                if api_patch(f'/tickets/{selected["id"]}/assign', {"assigned_agent_id": agent_map[chosen]}):
                    st.success("Ticket assigned")
                    st.rerun()
        status = st.selectbox("Update status", ["Open", "In Progress", "Waiting for User", "Resolved"])
        if st.button("Update status"):
            if api_patch(f'/tickets/{selected["id"]}/status', {"status": status}):
                st.success("Status updated")
                st.rerun()
        priority = st.selectbox("Change priority", ["Critical", "High", "Medium", "Low"], index=["Critical", "High", "Medium", "Low"].index(selected["priority"]))
        category = st.text_input("Change category", value=selected["category"])
        if st.button("Save ticket changes"):
            if api_patch(f'/tickets/{selected["id"]}', {"priority": priority, "category": category}):
                st.success("Ticket updated")
                st.rerun()
        st.subheader("Comments and internal notes")
        comments = api_get(f'/tickets/{selected["id"]}/comments') or []
        if comments:
            st.dataframe(comments, use_container_width=True)
        message = st.text_area("Message")
        internal = st.checkbox("Internal note (not visible to employee)")
        if st.button("Add message"):
            if api_post(f'/tickets/{selected["id"]}/comments', {"content": message, "is_internal": internal}):
                st.success("Message added")
                st.rerun()
        resolution = st.text_area("Resolution details")
        if st.button("Resolve ticket"):
            if api_patch(f'/tickets/{selected["id"]}/resolve', {"resolution_details": resolution}):
                st.success("Ticket resolved")
                st.rerun()
        if st.button("Request AI assistance"):
            result = api_post(f'/tickets/{selected["id"]}/ai-assistance', {})
            if result:
                st.subheader("AI assistance response")
                st.json(result)
        history = api_get(f'/tickets/{selected["id"]}/history') or []
        with st.expander("Ticket history"):
            st.dataframe(history, use_container_width=True)

def admin_page():
    st.header("Admin Dashboard")
    stats = api_get("/dashboard/stats")
    if stats:
        c1, c2 = st.columns(2)
        c1.metric("Total tickets", stats["total_tickets"])
        c2.metric("SLA breaches", stats["sla_breaches"])
        st.write("Status distribution")
        st.json(stats["status_distribution"])
        st.write("Priority distribution")
        st.json(stats["priority_distribution"])
    st.subheader("Users")
    users = api_get("/users")
    if users:
        st.dataframe(users, use_container_width=True)
    st.subheader("Register IT asset")
    employees = [u for u in (users or []) if u["role"] == "employee"]
    employee_map = {f'{u["name"]} (ID {u["id"]})': u["id"] for u in employees}
    with st.form("asset_form"):
        asset_name = st.text_input("Asset name")
        asset_type = st.selectbox("Asset type", ["Laptop", "Desktop", "Printer", "Monitor", "Router", "Other"])
        serial = st.text_input("Serial number")
        department = st.text_input("Department")
        employee_choice = st.selectbox("Assign employee", ["None"] + list(employee_map.keys()))
        submitted = st.form_submit_button("Register asset")
        if submitted:
            result = api_post("/assets", {"asset_name": asset_name, "asset_type": asset_type, "serial_number": serial, "department": department or None, "assigned_employee_id": employee_map.get(employee_choice)})
            if result:
                st.success("Asset registered")
                st.rerun()
    st.subheader("Assets")
    assets = api_get("/assets") or []
    if assets:
        st.dataframe(assets, use_container_width=True)
        asset_id = st.number_input("Asset ID to deactivate", min_value=1, step=1)
        if st.button("Deactivate asset"):
            if api_patch(f"/assets/{int(asset_id)}/deactivate"):
                st.success("Asset deactivated")
                st.rerun()
    st.subheader("Configure SLA rules")
    rules = api_get("/sla/rules") or []
    for rule in rules:
        with st.expander(rule["priority"]):
            response_hours = st.number_input("Response hours", min_value=0.1, value=float(rule["response_hours"]), key=f'r_{rule["priority"]}')
            resolution_hours = st.number_input("Resolution hours", min_value=0.1, value=float(rule["resolution_hours"]), key=f's_{rule["priority"]}')
            if st.button(f'Save {rule["priority"]} SLA'):
                if api_put(f'/sla/rules/{rule["priority"]}', {"response_hours": response_hours, "resolution_hours": resolution_hours}):
                    st.success("SLA updated")
                    st.rerun()

if not st.session_state.token:
    login_page()
else:
    user = st.session_state.user
    st.sidebar.write(f'Logged in: {user["name"]}')
    st.sidebar.write(f'Role: {user["role"]}')
    if st.sidebar.button("Logout"):
        st.session_state.token = None
        st.session_state.user = None
        st.rerun()
    if user["role"] == "employee":
        employee_page()
    elif user["role"] == "support_agent":
        agent_page()
    elif user["role"] == "admin":
        admin_page()

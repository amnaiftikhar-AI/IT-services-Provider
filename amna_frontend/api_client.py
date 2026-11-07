import requests
import streamlit as st


def headers():
    token = st.session_state.get("jwt_token", "").strip()
    user_id = st.session_state.get("user_id", "demo-amna")
    role = st.session_state.get("user_role", "admin")
    result = {"X-User-ID": user_id, "X-User-Role": role}
    if token: result["Authorization"] = f"Bearer {token}"
    return result

def request(method, path, **kwargs):
    base = st.session_state.get("api_url", "http://127.0.0.1:8000").rstrip("/")
    try:
        response = requests.request(method, base + path, headers=headers(), timeout=180, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        st.error(f"API request failed: {detail}")
        return None

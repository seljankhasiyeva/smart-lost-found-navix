import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Smart Lost & Found", layout="wide")
st.title("Smart Lost & Found")
st.caption("AI-powered item matching system")

tab1, tab2, tab3 = st.tabs(["Register Item", "Find Matches", "All Items"])

with tab1:
    st.subheader("Register a new item")
    with st.form("register_form"):
        col1, col2 = st.columns(2)
        with col1:
            uploaded_file = st.file_uploader("Upload Image (JPG/PNG):", type=["jpg", "png"])
        with col2:
            status = st.radio("Item Status:", ["lost", "found"], horizontal=True)
            description = st.text_area("Description:", placeholder="e.g. Black Nike backpack", height=120)
        submitted = st.form_submit_button("Submit Registration")
    if submitted:
        if uploaded_file and description:
            files = {"image": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            data = {"text": description}
            try:
                response = requests.post(f"{API_URL}/items/{status}", files=files, data=data)
                if response.status_code == 200:
                    st.success(f"Registered! Item ID: `{response.json().get('item_id')}`")
                else:
                    st.error(f"Error: {response.text}")
            except Exception as e:
                st.error(f"Connection error: {e}")
        else:
            st.warning("Please provide both image and description.")

with tab2:
    st.subheader("Find matches")
    item_id = st.text_input("Item ID:", placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000")
    k = st.slider("Number of matches:", 1, 10, 3)
    if st.button("Search Matches"):
        if item_id:
            try:
                res = requests.get(f"{API_URL}/items/{item_id}/matches", params={"k": k})
                if res.status_code == 200:
                    matches = res.json()
                    if not matches:
                        st.info("No matches found.")
                    else:
                        for i, m in enumerate(matches, 1):
                            with st.expander(f"Match {i} — Score: {m.get('score', 0):.2f}"):
                                st.write(f"**Item ID:** {m.get('item', {}).get('id', 'N/A')}")
                                st.write(f"**Status:** {m.get('item', {}).get('status', 'N/A')}")
                                st.write(f"**Description:** {m.get('item', {}).get('user_text', 'N/A')}")
                                st.write(f"**Reason:** {m.get('reason', 'N/A')}")
                else:
                    st.error(f"Error: {res.text}")
            except Exception as e:
                st.error(f"Connection error: {e}")
        else:
            st.warning("Please enter an Item ID.")

with tab3:
    st.subheader("All items")
    col1, col2 = st.columns([2, 1])
    with col1:
        status_filter = st.radio("Filter by status:", ["All", "lost", "found"], horizontal=True)
    with col2:
        refresh = st.button("Refresh List")
    if refresh:
        try:
            params = {} if status_filter == "All" else {"status": status_filter}
            res = requests.get(f"{API_URL}/items", params=params)
            if res.status_code == 200:
                items = res.json()
                if not items:
                    st.info("No items found.")
                else:
                    for item in items:
                        with st.expander(f"{item.get('status', '').upper()} — {item.get('user_text', '')[:50]}"):
                            st.write(f"**ID:** {item.get('id')}")
                            st.write(f"**Status:** {item.get('status')}")
                            st.write(f"**Description:** {item.get('user_text')}")
                            st.write(f"**Image:** {item.get('image_path')}")
            else:
                st.error("Failed to fetch items.")
        except Exception as e:
            st.error(f"Connection error: {e}")

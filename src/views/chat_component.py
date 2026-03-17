import streamlit as st
import pandas as pd
import time
from sqlalchemy import text

# Initialize connection at the top of your module
conn = st.connection("postgresql", type="sql")

# --- 1. THE DECORATOR (This enables auto-refresh) ---
# 'run_every=5' means this specific part of the screen reloads every 5 seconds.
@st.fragment(run_every=5)
def render_chat_widget():
    # REMOVED: db = st.session_state.supabase
    my_id = st.session_state.user.id
    my_role = st.session_state.user_role # Ensure this matches your auth.py session state

    st.header("💬 Team Chat")

    # --- 2. DETERMINE CONTACT LIST ---
    # Employees -> Can see Managers & Owner
    # Managers/Owners -> Can see Everyone
    # NEW POSTGRES QUERY (Using 'users' table instead of 'profiles')
    if my_role == 'employee':
        sql_contacts = text("SELECT id, full_name, role FROM users WHERE role IN ('manager', 'owner')")
        contacts_df = conn.query(sql_contacts, ttl=0)
    else:
        sql_contacts = text("SELECT id, full_name, role FROM users WHERE id != :my_id")
        contacts_df = conn.query(sql_contacts, params={"my_id": my_id}, ttl=0)
        
    if contacts_df.empty:
        st.info("No contacts available to chat.")
        return

    # --- 3. SELECT CONTACT ---
    # We use a key based on user ID to prevent the dropdown from resetting on auto-refresh
    contacts_list = contacts_df.to_dict('records')
    contact_map = {f"{c['full_name']} ({c['role'].capitalize()})": str(c['id']) for c in contacts_list}
    
    # Defaults to the first contact if none selected
    selected_name = st.selectbox(
        "Select Conversation", 
        list(contact_map.keys()), 
        key="chat_contact_select"
    )
    receiver_id = contact_map[selected_name]

    # --- 4. FETCH MESSAGES (Auto-runs every 5s) ---
    # NEW POSTGRES QUERY
    sql_msg = text("""
        SELECT * FROM direct_messages 
        WHERE (sender_id = :my_id AND receiver_id = :receiver_id) 
           OR (sender_id = :receiver_id AND receiver_id = :my_id)
        ORDER BY created_at ASC
    """)
    messages_df = conn.query(sql_msg, params={"my_id": my_id, "receiver_id": receiver_id}, ttl=0)

    # Container for chat history
    chat_container = st.container(height=400, border=True)
    
    with chat_container:
        if not messages_df.empty:
            messages_list = messages_df.to_dict('records')
            for msg in messages_list:
                # Convert UUIDs to strings to ensure matching works perfectly
                is_me = str(msg['sender_id']) == str(my_id)
                
                with st.chat_message("user" if is_me else "assistant"):
                    st.write(msg['message'])
                    # Timestamp conversion with utc=True fix
                    ts = pd.to_datetime(msg['created_at'], utc=True).tz_convert('Asia/Kolkata').strftime('%I:%M %p')
                    st.caption(f"{ts}")
        else:
            st.caption("No messages yet. Start the conversation!")

    # --- 5. SEND INPUT ---
    # When you send a message, we manually rerun immediately to show it
    if prompt := st.chat_input(f"Message {selected_name}..."):
        try:
            # NEW POSTGRES INSERT
            with conn.session as s:
                sql_insert = text("""
                    INSERT INTO direct_messages (sender_id, receiver_id, message) 
                    VALUES (:sender, :receiver, :msg)
                """)
                s.execute(sql_insert, {"sender": my_id, "receiver": receiver_id, "msg": prompt})
                s.commit()
            
            st.rerun() # Instant update on send
        except Exception as e:
            st.error(f"Failed to send: {e}")

    # --- 6. MANUAL REFRESH (Just in Case) ---
    # The 'run_every' handles it mostly, but this is good for network lag
    if st.button("🔄 Force Refresh"):
        st.rerun()
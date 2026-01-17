import streamlit as st
import time
import pandas as pd # Needed for time formatting
from streamlit_js_eval import get_geolocation
# REMOVED: from src.services.supabase_client import supabase (This caused the bug)
from src.services.geolocation import check_geofence
from src.auth import logout_user

def render_emp_dashboard():
    # --- 0. GET USER'S PRIVATE CONNECTION ---
    # This grabs the unique client created in init_session()
    db = st.session_state.supabase 

    # Sidebar
    st.sidebar.title(f"Pioneer View: {st.session_state.get('user_name', 'Employee')}")
    menu = st.sidebar.radio("My Workspace", ["Time Clock", "My Tasks", "Blind Messenger"])
    
    if st.sidebar.button("Logout"):
        logout_user()

    # --- 1. SMART TIME CLOCK ---
    if menu == "Time Clock":
        st.header("⏱️ Daily Attendance")
        
        # A. CHECK STATUS: Is there an unfinished shift?
        uid = st.session_state.user.id
        
        # USE 'db' INSTEAD OF 'supabase'
        active_shift = db.table("attendance_logs")\
            .select("*")\
            .eq("employee_id", uid)\
            .is_("clock_out", "null")\
            .execute()

        # B. LOGIC BRANCH: CLOCK OUT vs CLOCK IN
        if active_shift.data:
            # --- STATUS: WORKING (Show Clock Out) ---
            shift = active_shift.data[0]
            start_time = pd.to_datetime(shift['clock_in']).strftime('%H:%M')
            
            st.info(f"🟢 **YOU ARE CLOCKED IN** (Started at {start_time})")
            
            with st.form("clock_out_form"):
                st.write("End your shift?")
                comment = st.text_area("Daily Report / Comments", placeholder="Example: Finished 3 logo drafts. Uploading to vault.")
                
                if st.form_submit_button("🔴 CLOCK OUT NOW"):
                    # USE 'db'
                    db.table("attendance_logs").update({
                        "clock_out": "now()", 
                        "comments": comment,
                        "status": "completed" # Good practice to close status
                    }).eq("id", shift['id']).execute()
                    
                    st.success("Shift ended. Have a great evening!")
                    st.rerun()
                    
        else:
            # --- STATUS: OFFLINE (Show Clock In with Geofence) ---
            st.warning("⚪ You are currently OFFLINE")
            
            st.write("📍 **Verifying Location...**")
            loc = get_geolocation() 
            
            if loc:
                lat = loc['coords']['latitude']
                lon = loc['coords']['longitude']
                is_inside, dist = check_geofence(lat, lon)
                
                if dist > 1000:
                    st.metric("Distance to Office", f"{dist/1000:.1f} km")
                else:
                    st.metric("Distance to Office", f"{dist} m")
                
                if is_inside:
                    st.success("✅ Location Verified: Inside Office Zone")
                    if st.button("🟢 CLOCK IN"):
                        try:
                            # 1. Force fetch the ID from the current session state
                            current_user_id = st.session_state.user.id
                            
                            # 2. Insert using 'db' (Private Client)
                            db.table("attendance_logs").insert({
                                "employee_id": current_user_id,
                                "location_lat": lat, 
                                "location_long": lon,
                                "is_verified": True,
                                "status": "active" # Make sure you added this column, or remove this line
                            }).execute()
                            
                            st.balloons()
                            time.sleep(1) 
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error during Clock In: {e}")
                            st.write(f"⚠️ Debug Info - Failed for User ID: {st.session_state.user.id}")

                else:
                    st.error("❌ Outside Geofence Range")
                    st.button("🚫 Clock In Disabled", disabled=True)
            else:
                st.warning("⚠️ Waiting for GPS... (Please allow location access)")

    # --- 2. MY TASKS ---
    elif menu == "My Tasks":
        st.header("📋 My To-Do List")
        uid = st.session_state.user.id
        
        # USE 'db'
        tasks = db.table("tasks")\
            .select("*")\
            .eq("assigned_to", uid)\
            .order("created_at", desc=True)\
            .execute()
        
        if tasks.data:
            for t in tasks.data:
                status_icon = "✅" if t['status'] == 'done' else "⏳"
                
                with st.expander(f"{status_icon} {t['title']} ({t['status'].upper()})"):
                    st.write(t.get('description', 'No description provided.'))
                    st.caption(f"Assigned: {t['created_at'][:10]}")
                    
                    if t['status'] != 'done':
                        if st.button("Mark as Done", key=f"task_{t['id']}"):
                            # USE 'db'
                            db.table("tasks").update({"status": "done"}).eq("id", t['id']).execute()
                            st.toast("Task completed!")
                            st.rerun()
        else:
            st.info("No tasks assigned to you yet! Enjoy the coffee ☕")

    # --- 3. BLIND MESSENGER ---
    elif menu == "Blind Messenger":
        st.header("🕵️ Blind Messenger")
        st.caption("Securely message clients.")
        
        # USE 'db'
        clients = db.table("clients").select("id, name").execute()
        
        if clients.data:
            c_map = {c['name']: c['id'] for c in clients.data}
            
            target = st.selectbox("Select Client", list(c_map.keys()))
            msg = st.text_area("Message Body", height=150)
            
            if st.button("🚀 Send Secure Message"):
                if msg:
                    try:
                        # USE 'db'
                        db.table("communications").insert({
                            "client_id": c_map[target],
                            "sender_id": st.session_state.user.id,
                            "message_body": msg,
                            "direction": "outbound",
                            "status": "queued" 
                        }).execute()
                        st.success("Message queued! The relay system will deliver it shortly.")
                    except Exception as e:
                        st.error(f"Error sending message: {e}")
                else:
                    st.warning("Please write a message first.")
        else:
            st.info("No clients available to message.")
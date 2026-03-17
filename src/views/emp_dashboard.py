import streamlit as st
import time
import pandas as pd # Needed for time formatting
from sqlalchemy import text
from streamlit_js_eval import get_geolocation # Re-added to prevent missing function error

# Initialize connection at the top of your render function
conn = st.connection("postgresql", type="sql")
# REMOVED: from src.services.supabase_client import supabase (This caused the bug)
from src.services.geolocation import check_geofence
from src.auth import logout_user
from src.views.chat_component import render_chat_widget

def render_emp_dashboard():
    st.sidebar.title(f"Pioneer View: {st.session_state.get('user_name', 'Employee')}")
    menu = st.sidebar.radio("My Workspace", ["Time Clock", "My Tasks", "Team Chat"])
    
    if st.sidebar.button("Logout"):
        logout_user()

    # 1. SMART TIME CLOCK
    if menu == "Time Clock":
        st.header("⏱️ Daily Attendance")
        
        # A. CHECK STATUS: Is there an unfinished shift?
        uid = st.session_state.user.id
        
        # NEW POSTGRES QUERY
        active_shift_sql = text("SELECT * FROM attendance_logs WHERE employee_id = :uid AND clock_out IS NULL")
        active_shift_df = conn.query(active_shift_sql, params={"uid": uid}, ttl=0)

        # B. LOGIC BRANCH: CLOCK OUT vs CLOCK IN
        if not active_shift_df.empty:
            # --- STATUS: WORKING (Show Clock Out) ---
            shift = active_shift_df.iloc[0].to_dict()
            
            # --- FIX: ROBUST TIMEZONE CONVERSION ---
            try:
                start_time = pd.to_datetime(shift['clock_in'], utc=True).tz_convert('Asia/Kolkata').strftime('%H:%M')
            except Exception:
                start_time = "--:--"
            
            st.info(f"🟢 **YOU ARE CLOCKED IN** (Started at {start_time})")
            
            with st.form("clock_out_form"):
                st.write("End your shift?")
                comment = st.text_area("Daily Report / Comments", placeholder="Example: Finished 3 logo drafts. Uploading to vault.")
                
                if st.form_submit_button("🔴 CLOCK OUT NOW"):
                    # NEW POSTGRES UPDATE
                    with conn.session as s:
                        sql = text("""
                            UPDATE attendance_logs 
                            SET clock_out = NOW(), comments = :comment, status = 'completed' 
                            WHERE id = :id
                        """)
                        s.execute(sql, {"comment": comment, "id": shift['id']})
                        s.commit()
                    
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
                            
                            # 2. Insert using Postgres Connection
                            with conn.session as s:
                                sql = text("""
                                    INSERT INTO attendance_logs 
                                    (employee_id, clock_in, location_lat, location_long, is_verified, status) 
                                    VALUES (:uid, NOW(), :lat, :lon, true, 'active')
                                """)
                                s.execute(sql, {"uid": current_user_id, "lat": lat, "lon": lon})
                                s.commit()
                            
                            st.balloons()
                            time.sleep(1) 
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error during Clock In: {e}")
                            st.write(f"⚠️ Debug Info - Failed for User ID: {st.session_state.user.id}")

                else:
                    st.error("❌ Outside Office Range")
                    st.button("🚫 Clock In Disabled", disabled=True)
            else:
                st.warning("⚠️ Waiting for GPS... (Please allow location access)")

    # --- 2. MY TASKS ---
    elif menu == "My Tasks":
        st.header("📋 My To-Do List")
        uid = st.session_state.user.id
        
        # NEW POSTGRES QUERY
        tasks_sql = text("SELECT * FROM tasks WHERE assigned_to = :uid ORDER BY created_at DESC")
        tasks_df = conn.query(tasks_sql, params={"uid": uid}, ttl=0)
        
        if not tasks_df.empty:
            tasks_list = tasks_df.to_dict('records')
            for t in tasks_list:
                status_icon = "✅" if t['status'] == 'done' else "⏳"
                
                with st.expander(f"{status_icon} {t['title']} ({t['status'].upper()})"):
                    st.write(t.get('description') or 'No description provided.')
                    st.caption(f"Assigned: {str(t['created_at'])[:10]}")
                    
                    if t['status'] != 'done':
                        if st.button("Mark as Done", key=f"task_{t['id']}"):
                            # NEW POSTGRES UPDATE
                            with conn.session as s:
                                sql = text("UPDATE tasks SET status = 'done', completed_at = NOW() WHERE id = :id")
                                s.execute(sql, {"id": t['id']})
                                s.commit()
                                
                            st.toast("Task completed!")
                            st.rerun()
        else:
            st.info("No tasks assigned to you yet! Enjoy the coffee ☕")
            
            
    elif menu == "Team Chat":
        render_chat_widget()

''' # --- 3. BLIND MESSENGER ---
    elif menu == "Blind Messenger":
        st.header("🕵️ Blind Messenger")
        st.caption("Securely message clients.")
        
        # NEW POSTGRES QUERY
        df_clients = conn.query("SELECT id, name FROM clients", ttl=0)
        
        if not df_clients.empty:
            c_map = dict(zip(df_clients['name'], df_clients['id']))
            
            target = st.selectbox("Select Client", list(c_map.keys()))
            msg = st.text_area("Message Body", height=150)
            
            if st.button("🚀 Send Secure Message"):
                if msg:
                    try:
                        # NEW POSTGRES INSERT
                        with conn.session as s:
                            sql = text("""
                                INSERT INTO communications (client_id, sender_id, message_body, direction, status) 
                                VALUES (:cid, :sid, :msg, 'outbound', 'queued')
                            """)
                            s.execute(sql, {
                                "cid": c_map[target], 
                                "sid": st.session_state.user.id, 
                                "msg": msg
                            })
                            s.commit()
                        st.success("Message queued! The relay system will deliver it shortly.")
                    except Exception as e:
                        st.error(f"Error sending message: {e}")
                else:
                    st.warning("Please write a message first.")
        else:
            st.info("No clients available to message.")'''
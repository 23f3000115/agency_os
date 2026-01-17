import streamlit as st
import time
import pandas as pd
# REMOVED: from src.services.supabase_client import supabase (This caused the session bug)
from src.auth import logout_user

def render_owner_dashboard():
    # --- 1. GET PRIVATE SESSION CONNECTION ---
    # This ensures the Owner uses their OWN connection, not a shared global one.
    db = st.session_state.supabase 

    st.sidebar.title(f"Admin: {st.session_state.get('user_name', 'Owner')}")

    menu = st.sidebar.radio("Navigation", [
        "Overwatch", 
        "Task Dispatcher", 
        "Task Tracker",      
        "The Vault", 
        "Manage Staff", 
        "Payroll", 
        "Settings"
    ])
    
    if st.sidebar.button("Logout"):
        logout_user()

    # --- 1. OVERWATCH ---
    if menu == "Overwatch":
        st.header("🔭 Live Agency Overwatch")
        
        # Create Tabs to separate "Now" from "The Past"
        tab_live, tab_history = st.tabs(["🔴 Live Activity", "📅 Attendance History"])

        # --- TAB 1: Live Feed (Latest 20) ---
        with tab_live:
            st.caption("The 20 most recent clock-ins/outs.")
            
            # USE 'db'
            res = db.table("attendance_logs")\
                .select("*, profiles(full_name)")\
                .order("clock_in", desc=True)\
                .limit(20)\
                .execute()
            
            if res.data:
                df = pd.DataFrame(res.data)
                df['Employee'] = df['profiles'].apply(lambda x: x.get('full_name') if x else 'Unknown')
                
                # TIMEZONE CONVERSION (UTC -> IST)
                df['clock_in'] = pd.to_datetime(df['clock_in'])
                # Convert to India Time
                df['Time'] = df['clock_in'].dt.tz_convert('Asia/Kolkata').dt.strftime('%I:%M %p (%d-%b)')
                
                st.dataframe(
                    df[['Employee', 'Time', 'status', 'is_verified']], 
                    hide_index=True, 
                    use_container_width=True
                )
            else:
                st.info("No recent activity.")

        # --- TAB 2: History (Filter by Date) ---
        with tab_history:
            st.caption("View attendance records for any specific day.")
            
            selected_date = st.date_input("Select Date to View", value=pd.to_datetime("today"))
            start_ts = f"{selected_date}T00:00:00"
            end_ts = f"{selected_date}T23:59:59"
            
            # USE 'db'
            history_res = db.table("attendance_logs")\
                .select("*, profiles(full_name)")\
                .gte("clock_in", start_ts)\
                .lte("clock_in", end_ts)\
                .order("clock_in", desc=True)\
                .execute()
            
            if history_res.data:
                df_hist = pd.DataFrame(history_res.data)
                df_hist['Employee'] = df_hist['profiles'].apply(lambda x: x.get('full_name') if x else 'Unknown')
                
                # PAYROLL MATH & TIMEZONE FIX
                df_hist['clock_in'] = pd.to_datetime(df_hist['clock_in'])
                df_hist['clock_out'] = pd.to_datetime(df_hist['clock_out'])
                
                def calc_hours(row):
                    if pd.isnull(row['clock_out']): return 0.0
                    diff = row['clock_out'] - row['clock_in']
                    return diff.total_seconds() / 3600

                df_hist['Hours'] = df_hist.apply(calc_hours, axis=1).map('{:,.2f}'.format)
                
                # Convert UTC to IST for Display
                df_hist['In'] = df_hist['clock_in'].dt.tz_convert('Asia/Kolkata').dt.strftime('%I:%M %p')
                df_hist['Out'] = df_hist['clock_out'].dt.tz_convert('Asia/Kolkata').dt.strftime('%I:%M %p').fillna("Working...")

                st.dataframe(
                    df_hist[['Employee', 'In', 'Out', 'Hours', 'comments', 'status']], 
                    hide_index=True, 
                    use_container_width=True
                )
                
                st.divider()
                st.metric("Total Present", len(df_hist))
            else:
                st.warning(f"No attendance records found for {selected_date}")

    # --- 2. TASK DISPATCHER ---
    elif menu == "Task Dispatcher":
        st.header("⚡ Task Dispatcher")
        
        # USE 'db'
        emps = db.table("profiles").select("id, full_name").eq("role", "employee").execute()
        emp_map = {e['full_name']: e['id'] for e in emps.data} if emps.data else {}
        
        # USE 'db'
        clients = db.table("clients").select("id, name").execute()
        client_map = {c['name']: c['id'] for c in clients.data} if clients.data else {}

        with st.form("assign_task"):
            c1, c2 = st.columns(2)
            with c1:
                title = st.text_input("Task Title")
                sel_client = st.selectbox("Client", options=list(client_map.keys()))
            with c2:
                assignee = st.selectbox("Assign To", options=list(emp_map.keys()))
                due = st.date_input("Due Date")
            
            desc = st.text_area("Description")
            
            if st.form_submit_button("Dispatch Task"):
                if title and sel_client and assignee:
                    # USE 'db'
                    db.table("tasks").insert({
                        "title": title, 
                        "description": desc,
                        "client_id": client_map[sel_client],
                        "assigned_to": emp_map[assignee],
                        "due_date": str(due), 
                        "status": "todo" 
                    }).execute()
                    st.success("Task Assigned!")
                    st.rerun()
                else:
                    st.error("Please fill in all fields.")

    # --- 3. TASK TRACKER ---
    elif menu == "Task Tracker":
        st.header("📊 Live Task Tracker")
        
        tab1, tab2, tab3 = st.tabs(["All Tasks", "Pending", "Completed"])
        
        # USE 'db'
        res = db.table("tasks")\
            .select("*, profiles(full_name), clients(name)")\
            .order("created_at", desc=True)\
            .execute()
        
        if res.data:
            df = pd.DataFrame(res.data)

            # Clean Data
            df['Client'] = df['clients'].apply(lambda x: x.get('name') if x else 'Unknown')
            df['Assignee'] = df['profiles'].apply(lambda x: x.get('full_name') if x else 'Unassigned')
            
            display_cols = ['title', 'Client', 'Assignee', 'status', 'due_date', 'description']
            
            df_display = df[display_cols].rename(columns={
                'title': 'Task',
                'status': 'Status',
                'due_date': 'Due Date',
                'description': 'Details'
            })

            with tab1:
                st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            with tab2:
                pending_df = df_display[df_display['Status'] != 'done']
                if not pending_df.empty:
                    st.dataframe(pending_df, use_container_width=True, hide_index=True)
                else:
                    st.success("No pending tasks!")

            with tab3:
                completed_df = df_display[df_display['Status'] == 'done']
                if not completed_df.empty:
                    st.dataframe(completed_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No completed tasks yet.")
        else:
            st.info("No tasks found in the database.")

    # --- 4. THE VAULT ---
    elif menu == "The Vault":
        st.header("🔐 Client Vault")
        st.info("Add clients here. Emails are hidden from employees.")
        
        with st.expander("➕ Add New Client"):
            with st.form("add_client"):
                name = st.text_input("Company Name")
                email = st.text_input("Contact Email")
                
                if st.form_submit_button("Save to Vault"):
                    if name and email:
                        try:
                            # USE 'db'
                            db.table("clients").insert({
                                "name": name, 
                                "email": email
                            }).execute()
                            st.success("Client Added Securely")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.warning("Name and Email are required.")
        
        st.subheader("🗄 Client Database")
        
        # USE 'db'
        clients = db.table("clients").select("*").execute()
        
        if clients.data:
            for client in clients.data:
                display_name = client.get('name', 'Unknown Client')
                
                with st.expander(f"🏢 {display_name}"):
                    c1, c2 = st.columns([3, 1])
                    
                    with c1:
                        st.write(f"**Email:** {client.get('email', 'No Email')}")
                        st.caption(f"ID: {client['id']}")
                    
                    with c2:
                        st.write("") 
                        if st.button("🗑️ Delete", key=f"del_client_{client['id']}"):
                            try:
                                # USE 'db'
                                db.rpc("delete_client", {"target_id": client['id']}).execute()
                                st.toast("Deleted!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
        else:
            st.info("The Vault is empty.")

    # --- 5. PAYROLL ENGINE ---
    elif menu == "Payroll":
        st.header("💰 Monthly Payroll Calculator")
        st.caption("Calculate exact payouts based on verified attendance hours.")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            months = ["January", "February", "March", "April", "May", "June", 
                      "July", "August", "September", "October", "November", "December"]
            sel_month = st.selectbox("Select Month", months, index=0)
        with col2:
            sel_year = st.number_input("Year", value=2026, step=1)
        with col3:
            st.write("")
            run_calc = st.button("🧮 Run Payroll", type="primary")

        if run_calc:
            with st.spinner("Crunching the numbers..."):
                month_idx = months.index(sel_month) + 1
                start_date = f"{sel_year}-{month_idx:02d}-01"
                next_month_ts = pd.Timestamp(start_date) + pd.DateOffset(months=1)
                
                # USE 'db'
                logs = db.table("attendance_logs")\
                    .select("*")\
                    .gte("clock_in", start_date)\
                    .lt("clock_in", next_month_ts.strftime('%Y-%m-%d'))\
                    .execute()
                
                # USE 'db'
                emps = db.table("profiles").select("id, full_name, hourly_rate").eq("role", "employee").execute()
                
                if logs.data and emps.data:
                    df_logs = pd.DataFrame(logs.data)
                    df_emps = pd.DataFrame(emps.data)
                    
                    # Filter incomplete shifts
                    df_logs = df_logs[df_logs['clock_out'].notnull()].copy()
                    
                    # Calculate Hours
                    df_logs['clock_in'] = pd.to_datetime(df_logs['clock_in'])
                    df_logs['clock_out'] = pd.to_datetime(df_logs['clock_out'])
                    df_logs['shift_hours'] = (df_logs['clock_out'] - df_logs['clock_in']).dt.total_seconds() / 3600
                    
                    summary = df_logs.groupby('employee_id')['shift_hours'].sum().reset_index()
                    
                    final_df = pd.merge(summary, df_emps, left_on='employee_id', right_on='id', how='left')
                    
                    final_df['hourly_rate'] = final_df['hourly_rate'].fillna(0)
                    final_df['Total Pay'] = final_df['shift_hours'] * final_df['hourly_rate']
                    
                    st.divider()
                    
                    total_outflow = final_df['Total Pay'].sum()
                    st.subheader(f"💸 Total Outflow: ₹{total_outflow:,.2f}")
                    
                    final_df['Employee'] = final_df['full_name']
                    final_df['Hours Worked'] = final_df['shift_hours'].map('{:,.2f}'.format)
                    final_df['Rate'] = final_df['hourly_rate'].map('₹{:,.2f}/hr'.format)
                    final_df['Payout (₹)'] = final_df['Total Pay'].map('₹{:,.2f}'.format)
                    
                    st.dataframe(
                        final_df[['Employee', 'Hours Worked', 'Rate', 'Payout (₹)']],
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    csv = final_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Download CSV for Bank",
                        csv,
                        f"payroll_{sel_month}_{sel_year}.csv",
                        "text/csv"
                    )
                else:
                    st.warning(f"No completed attendance records found for {sel_month} {sel_year}.")

    # --- 6. MANAGE STAFF ---
    elif menu == "Manage Staff":
        st.header("👥 Workforce Management")
        
        # --- A. HIRE NEW EMPLOYEE ---
        with st.expander("➕ Hire New Employee", expanded=True):
            with st.form("hire_employee"):
                col1, col2 = st.columns(2)
                with col1:
                    new_emp_name = st.text_input("Full Name", placeholder="Rahul Sharma")
                    new_emp_email = st.text_input("Email", placeholder="rahul@agency.com").strip()
                with col2:
                    new_emp_pass = st.text_input("Password", type="password").strip()
                    new_emp_rate = st.number_input("Hourly Rate (₹)", min_value=0.0, value=500.0, step=50.0)
                
                submitted = st.form_submit_button("Create Employee Account")
                
                if submitted:
                    if not new_emp_email or not new_emp_pass or not new_emp_name:
                        st.error("Please fill in ALL fields.")
                    else:
                        try:
                            # 1. SPECIAL ADMIN CLIENT (Needs Service Key)
                            from supabase import create_client
                            try:
                                sb_url = st.secrets["supabase"]["url"]
                                sb_service_key = st.secrets["supabase"]["service_key"]
                            except KeyError:
                                st.error("❌ Missing 'service_key' in secrets.toml")
                                st.stop()

                            admin_supabase = create_client(sb_url, sb_service_key)

                            # 2. Create User via Admin API
                            admin_supabase.auth.admin.create_user({
                                "email": new_emp_email,
                                "password": new_emp_pass,
                                "email_confirm": True,
                                "user_metadata": { "full_name": new_emp_name }
                            })
                            
                            time.sleep(1.5)
                            
                            # 3. Update the Hourly Rate using 'db' (Owner's Connection)
                            user_res = db.table("profiles").select("id").eq("email", new_emp_email).execute()
                            
                            if user_res.data:
                                uid = user_res.data[0]['id']
                                # USE 'db'
                                db.table("profiles").update({
                                    "hourly_rate": new_emp_rate
                                }).eq("id", uid).execute()
                            
                            st.success(f"✅ Welcome to the team, {new_emp_name}! Rate set to ₹{new_emp_rate}/hr.")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()

                        except Exception as e:
                            st.error(f"Error creating employee: {e}")

        st.divider()
        st.subheader("📋 Active Staff Registry")
        
        # USE 'db'
        staff = db.table("profiles").select("*").eq("role", "employee").order("created_at").execute()
        
        if staff.data:
            for employee in staff.data:
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                    
                    with c1:
                        st.write(f"**{employee.get('full_name', 'Unknown')}**")
                        st.caption(f"📧 {employee['email']}")
                    with c2:
                        rate = employee.get('hourly_rate', 0)
                        st.write(f"💰 Rate: **₹{rate}/hr**")
                    with c3:
                        st.write(f"Joined: {employee.get('created_at', '')[:10]}")
                    with c4:
                        if st.button("🔥", key=f"fire_{employee['id']}", help="Fire Employee"):
                            try:
                                # USE 'db'
                                db.rpc("delete_employee", {"target_email": employee['email']}).execute()
                                st.success("Removed.")
                                time.sleep(0.5)
                                st.rerun() 
                            except Exception as e:
                                st.error(f"Err: {e}")

                    with st.expander(f"✏️ Edit {employee.get('full_name')}'s Details"):
                        with st.form(f"edit_form_{employee['id']}"):
                            edit_name = st.text_input("Name", value=employee.get('full_name', ''))
                            edit_email = st.text_input("Contact Email", value=employee.get('email', ''))
                            edit_rate = st.number_input("Hourly Rate ($)", value=float(employee.get('hourly_rate', 0.0)), step=0.5)
                            
                            if st.form_submit_button("💾 Save Changes"):
                                try:
                                    # USE 'db'
                                    db.table("profiles").update({
                                        "full_name": edit_name,
                                        "email": edit_email,
                                        "hourly_rate": edit_rate
                                    }).eq("id", employee['id']).execute()
                                    
                                    st.success("Details updated successfully!")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Could not update: {e}")
        else:
            st.info("No active employees found.")

    # --- 7. SETTINGS ---
    elif menu == "Settings":
        st.header("⚙️ Personal Settings")
        
        current_name = st.session_state.get('user_name', '')
        new_name = st.text_input("Update My Name", value=current_name)
        
        if st.button("Save Changes"):
            # USE 'db'
            db.table("profiles").update({"full_name": new_name}).eq("id", st.session_state.user.id).execute()
            st.session_state.user_name = new_name
            st.success("Name updated!")
            st.rerun()
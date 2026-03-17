import streamlit as st
import time
import pandas as pd
import bcrypt
from sqlalchemy import text

# Initialize connection at the top of your render function
conn = st.connection("postgresql", type="sql")
from src.auth import logout_user
from src.views.chat_component import render_chat_widget

def render_owner_dashboard():
    st.sidebar.title(f"Admin: {st.session_state.get('user_name', 'Owner')}")

    menu = st.sidebar.radio("Navigation", [
        "Overwatch", 
        "AI Insights",
        "Task Dispatcher", 
        "Task Tracker",      
        "The Vault", 
        "Manage Staff", 
        "Payroll", 
        "Team Chat",
        "Settings"
    ])
    
    if st.sidebar.button("Logout"):
        logout_user()

    # --- 1. OVERWATCH ---
    if menu == "Overwatch":
        st.header("🔭 Live Agency Overwatch")
        
        tab_live, tab_history = st.tabs(["🔴 Live Activity", "📅 Attendance History"])

        # --- TAB 1: Live Feed (Latest 20) ---
        with tab_live:
            st.caption("The 20 most recent clock-ins/outs.")
            
            # Use raw SQL with JOIN to get the user's name
            sql = """
                SELECT a.*, u.full_name as employee_name 
                FROM attendance_logs a 
                LEFT JOIN users u ON a.employee_id = u.id 
                ORDER BY a.clock_in DESC LIMIT 20
            """
            df = conn.query(sql, ttl=0)
            
            if not df.empty:
                df['Employee'] = df['employee_name'].fillna('Unknown')
                
                # TIMEZONE CONVERSION (UTC -> IST)
                df['clock_in'] = pd.to_datetime(df['clock_in'], utc=True)
                df['Time'] = df['clock_in'].dt.tz_convert('Asia/Kolkata').dt.strftime('%I:%M %p (%d-%b)')
                
                st.dataframe(
                    df[['Employee', 'Time', 'status', 'is_verified']], 
                    hide_index=True, 
                    use_container_width=True
                )
            else:
                st.info("No recent activity.")
                
        with tab_history:
            st.caption("View attendance records for any specific day.")
            
            selected_date = st.date_input("Select Date to View", value=pd.to_datetime("today"))
            start_ts = f"{selected_date} 00:00:00"
            end_ts = f"{selected_date} 23:59:59"
            
            sql = """
                SELECT a.*, u.full_name as employee_name 
                FROM attendance_logs a 
                LEFT JOIN users u ON a.employee_id = u.id 
                WHERE a.clock_in >= :start_ts AND a.clock_in <= :end_ts
                ORDER BY a.clock_in DESC
            """
            df_hist = conn.query(sql, params={"start_ts": start_ts, "end_ts": end_ts}, ttl=0)
            
            if not df_hist.empty:
                df_hist['Employee'] = df_hist['employee_name'].fillna('Unknown')
                
                # PAYROLL MATH & TIMEZONE FIX
                df_hist['clock_in'] = pd.to_datetime(df_hist['clock_in'], utc=True)
                df_hist['clock_out'] = pd.to_datetime(df_hist['clock_out'], utc=True)
                
                def calc_hours(row):
                    if pd.isnull(row['clock_out']): return 0.0
                    diff = row['clock_out'] - row['clock_in']
                    return diff.total_seconds() / 3600

                df_hist['Hours'] = df_hist.apply(calc_hours, axis=1).map('{:,.2f}'.format)
                
                # Convert UTC to IST for Display
                df_hist['In'] = df_hist['clock_in'].dt.tz_convert('Asia/Kolkata').dt.strftime('%I:%M %p')
                df_hist['Out'] = df_hist['clock_out'].dt.tz_convert('Asia/Kolkata').dt.strftime('%I:%M %p').fillna("Working...")

                st.dataframe(
                    df_hist[['Employee', 'In', 'Out', 'Hours', 'status']], 
                    hide_index=True, 
                    use_container_width=True
                )
                
                st.divider()
                st.metric("Total Present", len(df_hist))
            else:
                st.warning(f"No attendance records found for {selected_date}")
                
        # --- NEW: AI INSIGHTS ---
    elif menu == "AI Insights":
        st.header("🧠 AI Operations Manager")
        st.caption("Live sentiment analysis from the n8n background engine.")

        # 1. Fetch Analyzed Communications
        sql = """
            SELECT c.message_body, c.ai_sentiment_score, c.ai_summary, c.created_at, 
                   cl.name as client_name, u.full_name as employee_name
            FROM communications c
            LEFT JOIN clients cl ON c.client_id = cl.id
            LEFT JOIN users u ON c.sender_id = u.id
            WHERE c.is_analyzed = TRUE
            ORDER BY c.created_at DESC
        """
        df_ai = conn.query(sql, ttl=0)

        if not df_ai.empty:
            # Clean up the dataframe
            df_ai['client_name'] = df_ai['client_name'].fillna('Unknown Client')
            df_ai['employee_name'] = df_ai['employee_name'].fillna('System/Client')
            
            # --- TOP METRICS ---
            avg_score = df_ai['ai_sentiment_score'].mean()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Avg Client Sentiment", f"{avg_score:.1f} / 10")
            with col2:
                st.metric("Analyzed Interactions", len(df_ai))
            with col3:
                # Find the lowest score to highlight immediate risks
                lowest_score = df_ai['ai_sentiment_score'].min()
                st.metric("Lowest Health Score", f"{lowest_score} / 10", delta="Requires Attention" if lowest_score < 5 else "All Good", delta_color="inverse")

            st.divider()

            # --- THE LIVE FEED ---
            st.subheader("📡 Live Sentiment Feed")
            
            for index, row in df_ai.iterrows():
                score = row['ai_sentiment_score']
                
                # Dynamic coloring based on the LLM's score
                if score >= 8:
                    color = "🟢"
                elif score >= 5:
                    color = "🟡"
                else:
                    color = "🔴"
                
                with st.expander(f"{color} {row['client_name']} (Score: {score}/10) - {str(row['created_at'])[:10]}"):
                    st.write(f"**AI Summary:** {row['ai_summary']}")
                    st.caption(f"**Original Message:** {row['message_body']}")
                    st.caption(f"Handled by: {row['employee_name']}")

            # --- EMPLOYEE LEADERBOARD ---
            st.divider()
            st.subheader("🏆 AI Employee Leaderboard")
            st.caption("Ranking employees by the average sentiment score of their client interactions.")
            
            # Group by employee and calculate their average client sentiment score
            leaderboard = df_ai.groupby('employee_name')['ai_sentiment_score'].mean().reset_index()
            leaderboard = leaderboard.sort_values(by='ai_sentiment_score', ascending=False)
            leaderboard.rename(columns={'employee_name': 'Employee', 'ai_sentiment_score': 'Avg Client Score'}, inplace=True)
            
            st.dataframe(leaderboard, hide_index=True, use_container_width=True)

        else:
            st.info("The AI Manager is waiting for data. Send a test message and let n8n process it!")

        # --- TAB 2: History (Filter by Date) ---
        

    # --- 2. TASK DISPATCHER ---
    elif menu == "Task Dispatcher":
        st.header("⚡ Task Dispatcher")
        
        emps_df = conn.query("SELECT id, full_name FROM users WHERE role = 'employee'", ttl=0)
        emp_map = dict(zip(emps_df['full_name'], emps_df['id'])) if not emps_df.empty else {}
        
        clients_df = conn.query("SELECT id, name FROM clients", ttl=0)
        client_map = dict(zip(clients_df['name'], clients_df['id'])) if not clients_df.empty else {}

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
                    with conn.session as s:
                        sql = text("""
                            INSERT INTO tasks (title, description, client_id, assigned_to, due_date, status) 
                            VALUES (:title, :desc, :cid, :aid, :due, 'todo')
                        """)
                        s.execute(sql, {
                            "title": title, "desc": desc, 
                            "cid": client_map[sel_client], "aid": emp_map[assignee], "due": due
                        })
                        s.commit()
                    st.success("Task Assigned!")
                    st.rerun()
                else:
                    st.error("Please fill in all fields.")

    # --- 3. TASK TRACKER ---
    elif menu == "Task Tracker":
        st.header("📊 Live Task Tracker")
        
        tab1, tab2, tab3 = st.tabs(["All Tasks", "Pending", "Completed"])
        
        sql = """
            SELECT t.*, u.full_name as assignee_name, c.name as client_name 
            FROM tasks t 
            LEFT JOIN users u ON t.assigned_to = u.id 
            LEFT JOIN clients c ON t.client_id = c.id 
            ORDER BY t.created_at DESC
        """
        df = conn.query(sql, ttl=0)
        
        if not df.empty:
            df['Client'] = df['client_name'].fillna('Unknown')
            df['Assignee'] = df['assignee_name'].fillna('Unassigned')
            
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
                            with conn.session as s:
                                sql = text("INSERT INTO clients (name, email) VALUES (:name, :email)")
                                s.execute(sql, {"name": name, "email": email})
                                s.commit()
                            st.success("Client Added Securely")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.warning("Name and Email are required.")
        
        st.subheader("🗄 Client Database")
        
        clients_df = conn.query("SELECT * FROM clients", ttl=0)
        
        if not clients_df.empty:
            clients = clients_df.to_dict('records')
            for client in clients:
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
                                with conn.session as s:
                                    sql = text("DELETE FROM clients WHERE id = :id")
                                    s.execute(sql, {"id": client['id']})
                                    s.commit()
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
                
                df_logs = conn.query("""
                    SELECT * FROM attendance_logs 
                    WHERE clock_in >= :start AND clock_in < :end
                """, params={"start": start_date, "end": next_month_ts.strftime('%Y-%m-%d')}, ttl=0)
                
                df_emps = conn.query("SELECT id, full_name, hourly_rate FROM users WHERE role = 'employee'", ttl=0)
                
                if not df_logs.empty and not df_emps.empty:
                    # Filter incomplete shifts
                    df_logs = df_logs[df_logs['clock_out'].notnull()].copy()
                    
                    # Calculate Hours
                    df_logs['clock_in'] = pd.to_datetime(df_logs['clock_in'], utc=True)
                    df_logs['clock_out'] = pd.to_datetime(df_logs['clock_out'], utc=True)
                    df_logs['shift_hours'] = (df_logs['clock_out'] - df_logs['clock_in']).dt.total_seconds() / 3600
                    
                    summary = df_logs.groupby('employee_id')['shift_hours'].sum().reset_index()
                    
                    # Ensure matching ID types before merge
                    summary['employee_id'] = summary['employee_id'].astype(str)
                    df_emps['id'] = df_emps['id'].astype(str)
                    
                    final_df = pd.merge(summary, df_emps, left_on='employee_id', right_on='id', how='left')
                    
                    # Convert columns to float to avoid typing errors
                    final_df['shift_hours'] = final_df['shift_hours'].astype(float)
                    final_df['hourly_rate'] = pd.to_numeric(final_df['hourly_rate'], errors='coerce').fillna(0.0)
                    
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
                            # HASH PASSWORD AND INSERT DIRECTLY TO POSTGRES
                            salt = bcrypt.gensalt()
                            hashed_pw = bcrypt.hashpw(new_emp_pass.encode('utf-8'), salt).decode('utf-8')
                            
                            with conn.session as s:
                                sql = text("""
                                    INSERT INTO users (full_name, email, password_hash, role, hourly_rate) 
                                    VALUES (:name, :email, :pw, 'employee', :rate)
                                """)
                                s.execute(sql, {"name": new_emp_name, "email": new_emp_email, "pw": hashed_pw, "rate": new_emp_rate})
                                s.commit()
                                
                            st.success(f"✅ Welcome to the team, {new_emp_name}! Rate set to ₹{new_emp_rate}/hr.")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()

                        except Exception as e:
                            st.error(f"Error creating employee (Email might already exist): {e}")

        st.divider()
        st.subheader("📋 Active Staff Registry")
        
        staff_df = conn.query("SELECT * FROM users WHERE role = 'employee' ORDER BY created_at", ttl=0)
        
        if not staff_df.empty:
            staff_records = staff_df.to_dict('records')
            for employee in staff_records:
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                    
                    with c1:
                        st.write(f"**{employee.get('full_name', 'Unknown')}**")
                        st.caption(f"📧 {employee['email']}")
                    with c2:
                        rate = employee.get('hourly_rate', 0)
                        st.write(f"💰 Rate: **₹{rate}/hr**")
                    with c3:
                        st.write(f"Joined: {str(employee.get('created_at', ''))[:10]}")
                    with c4:
                        if st.button("🔥", key=f"fire_{employee['id']}", help="Fire Employee"):
                            try:
                                with conn.session as s:
                                    sql = text("DELETE FROM users WHERE email = :email")
                                    s.execute(sql, {"email": employee['email']})
                                    s.commit()
                                st.success("Removed.")
                                time.sleep(0.5)
                                st.rerun() 
                            except Exception as e:
                                st.error(f"Err: {e}")

                    with st.expander(f"✏️ Edit {employee.get('full_name')}'s Details"):
                        with st.form(f"edit_form_{employee['id']}"):
                            edit_name = st.text_input("Name", value=employee.get('full_name', ''))
                            edit_email = st.text_input("Contact Email", value=employee.get('email', ''))
                            edit_rate = st.number_input("Hourly Rate (₹)", value=float(employee.get('hourly_rate') or 0.0), step=50.0)
                            
                            if st.form_submit_button("💾 Save Changes"):
                                try:
                                    with conn.session as s:
                                        sql = text("""
                                            UPDATE users SET full_name = :name, email = :email, hourly_rate = :rate 
                                            WHERE id = :id
                                        """)
                                        s.execute(sql, {"name": edit_name, "email": edit_email, "rate": edit_rate, "id": employee['id']})
                                        s.commit()
                                    
                                    st.success("Details updated successfully!")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Could not update: {e}")
        else:
            st.info("No active employees found.")
    
    elif menu == "Team Chat":
        render_chat_widget()

    # --- 7. SETTINGS ---
    elif menu == "Settings":
        st.header("⚙️ Personal Settings")
        
        current_name = st.session_state.get('user_name', '')
        new_name = st.text_input("Update My Name", value=current_name)
        
        if st.button("Save Changes"):
            with conn.session as s:
                sql = text("UPDATE users SET full_name = :name WHERE id = :id")
                s.execute(sql, {"name": new_name, "id": st.session_state.user.id})
                s.commit()
                
            st.session_state.user_name = new_name
            st.success("Name updated!")
            st.rerun()
import streamlit as st
import pandas as pd
import os
import shutil
from mysql.connector import Error
import backend  # Import logical backend

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="MySQL Provisioner Pro", page_icon="🛡️")

# --- USER INTERFACE (UI) ---
st.title("🛡️ MySQL Provisioning Tool (Enterprise)")
st.markdown("Secure database provisioning with **RBAC** & **IDM Support**.")

# Sidebar - Connection Settings
with st.sidebar:
    st.header("🔌 Server Connection")
    db_host = st.text_input("Database Host", value="localhost")
    db_port = st.text_input("Database Port", value="3306") 
    
    st.markdown("---")
    st.info("Log in with your IDM/AD Credentials")
    db_user = st.text_input("Your Username (e.g. j.smith)", value="")
    db_pass = st.text_input("Your Password", type="password")
    
    # Checkbox for Enterprise Authentication
    enterprise_auth = st.checkbox("Enterprise Auth (LDAP/PAM/IDM)", value=False, help="Enable this for Active Directory/LDAP credentials.")
    
    if st.button("Test Connection"):
        if not db_port.isdigit():
             st.error("Port must be a valid number!")
        else:
            try:
                conn = backend.get_db_connection(db_host, db_port, db_user, db_pass, enterprise_auth)
                if conn.is_connected():
                    st.success(f"Connected to {db_host} as {db_user} successfully!")
                    conn.close()
            except Error as e:
                st.error(f"Connection Failed: {e}")
            except ValueError:
                st.error("Port must be a valid number!")

# Main Section - File Upload
st.header("1. Upload Project Definitions")
st.info("Required Excel columns: `Project_Name`, `Environment`, `Roles` (e.g. app, batch, dbo, read)")
uploaded_file = st.file_uploader("Select Excel File", type=['xlsx'])

if uploaded_file is not None and db_pass:
    try:
        df = pd.read_excel(uploaded_file)
        
        # Verify required columns
        required_columns = ['Project_Name', 'Environment', 'Roles']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"❌ Missing required columns: {', '.join(missing_columns)}")
        else:
            st.dataframe(df.head())
            
            col1, col2 = st.columns(2)
            dry_run = col1.checkbox("Simulation Mode (Dry Run - No DB changes)", value=True)
            
            if st.button("🚀 RUN PROVISIONING", type="primary"):
                # Clean up previous temporary files
                if os.path.exists("DIST_TEMP"):
                    shutil.rmtree("DIST_TEMP")
                os.makedirs("DIST_TEMP")
                
                progress_bar = st.progress(0)
                master_list = []
                logs = []
                
                total_rows = len(df)
                has_errors = False
                
                for index, row in df.iterrows():
                    # --- INPUT VALIDATION ---
                    try:
                        project = backend.validate_identifier(str(row['Project_Name']).strip())
                        env = backend.validate_identifier(str(row['Environment']).strip())
                        raw_roles = str(row['Roles']).split(',')
                        roles = []
                        for r in raw_roles:
                            roles.append(backend.validate_identifier(r.strip()))
                    except ValueError as ve:
                        logs.append(f"❌ ROW {index+1}: Validation Error - {ve}")
                        has_errors = True
                        progress_bar.progress((index + 1) / total_rows)
                        continue
                    # ------------------------

                    db_name = f"{project.lower()}_{env.lower()}"
                    
                    # Prepare SQL Commands
                    sql_commands = []
                    sql_commands.append(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4;")
                    
                    project_users = []
                    
                    for role in roles:
                        username = f"{project.lower()}_{env.lower()}_{role.lower()}"
                        password = backend.generate_password()
                        
                        # Determine privileges based on role
                        privileges = backend.get_privileges_by_role(role)
                        
                        # Idempotent user creation logic
                        sql_commands.append(f"CREATE USER IF NOT EXISTS '{username}'@'%' IDENTIFIED BY '{password}';")
                        sql_commands.append(f"ALTER USER '{username}'@'%' IDENTIFIED BY '{password}';")
                        sql_commands.append(f"GRANT {privileges} ON {db_name}.* TO '{username}'@'%';")
                        
                        master_list.append({
                            'Project': project, 'Env': env, 'Role': role,
                            'Privileges': privileges, 'User': username, 'Pass': password,
                            'Host': f"{db_host}:{db_port}"
                        })
                        project_users.append({'role': role, 'user': username, 'password': password, 'privileges': privileges})

                    sql_commands.append("FLUSH PRIVILEGES;")
                    
                    # Execute SQL
                    if not dry_run:
                        try:
                            # Use backend connection
                            conn = backend.get_db_connection(db_host, db_port, db_user, db_pass, enterprise_auth)
                            cursor = conn.cursor()
                            for sql in sql_commands:
                                cursor.execute(sql)
                            conn.commit()
                            conn.close()
                            logs.append(f"✅ {project}: Successfully configured on port {db_port}.")
                        except Error as e:
                            logs.append(f"❌ {project}: SQL Error - {e}")
                    else:
                        logs.append(f"ℹ️ {project}: Simulation OK ({len(sql_commands)} commands prepared).")
                    
                    # Generate Output Files
                    backend.create_local_files(project, env, project_users, db_host, db_port)
                    progress_bar.progress((index + 1) / total_rows)

                # Final Summary
                st.markdown("---")
                if has_errors:
                     st.error("Some rows failed validation. Please check the logs below.")
                
                st.success("Provisioning Workflow Completed!")
                for log in logs:
                    st.text(log)
                    
                # Export Master Report
                if master_list:
                    master_df = pd.DataFrame(master_list)
                    master_filename = "MASTER_PASSWORDS_SECURE.xlsx"
                    master_df.to_excel(os.path.join("DIST_TEMP", master_filename), index=False)
                    
                    st.warning("⚠️ **SECURITY WARNING**: The Master Credentials file below contains PLAINTEXT passwords. Delete it after secure distribution!")
                    
                    with open(os.path.join("DIST_TEMP", master_filename), "rb") as f:
                        st.download_button("📥 Download Secure Master Report", f, file_name="Master_Credentials.xlsx")

                st.info("Developer .env files have been generated in the 'DIST_TEMP' folder.")
    except Exception as e:
        st.error(f"Error reading Excel file: {e}")

elif uploaded_file is not None and not db_pass:
    st.warning("⚠️ Please enter the Admin Password in the sidebar to proceed.")
import streamlit as st
import pandas as pd
import secrets
import string
import os
import mysql.connector
from datetime import datetime
from mysql.connector import Error
import shutil

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="MySQL Provisioner Pro", page_icon="🛡️")

# --- SECURITY LOGIC (RBAC) ---
def get_privileges_by_role(role_name):
    """Maps business role to MySQL Privileges."""
    role_upper = role_name.upper().strip()
    if role_upper in ['DBO', 'ADMIN', 'OWNER', 'MIGRATOR']:
        return "ALL PRIVILEGES"
    elif role_upper in ['RO', 'READ', 'READER', 'REPORT']:
        return "SELECT"
    else:
        return "SELECT, INSERT, UPDATE, DELETE, EXECUTE, SHOW VIEW"

# --- HELPER FUNCTIONS ---
def generate_password(length=20):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        if (any(c.islower() for c in password) and any(c.isupper() for c in password) and sum(c.isdigit() for c in password) >= 3):
            return password

def create_local_files(project_name, env, users_data, db_host, db_port):
    folder_name = f"{project_name}_{env}"
    base_path = os.path.join("DIST_TEMP", folder_name)
    os.makedirs(base_path, exist_ok=True)
    
    env_content = f"# Auto-generated config for {project_name} ({env})\n"
    env_content += f"# Generated on: {datetime.now()}\n"
    env_content += f"DB_HOST={db_host}\n"
    env_content += f"DB_PORT={db_port}\n"
    db_name = f"{project_name.lower()}_{env.lower()}"
    env_content += f"DB_NAME={db_name}\n\n"
    
    for user in users_data:
        role = user['role'].upper()
        privs = user['privileges']
        env_content += f"# Role: {role} (Privileges: {privs})\n"
        env_content += f"DB_USER_{role}={user['user']}\n"
        env_content += f"DB_PASS_{role}={user['password']}\n"
    
    with open(os.path.join(base_path, ".env"), "w") as f:
        f.write(env_content)

def get_db_connection(host, port, user, password, use_enterprise_auth):
    """Handles connection logic depending on Auth Type."""
    config = {
        'host': host,
        'port': int(port),
        'user': user,
        'password': password,
        'connect_timeout': 10
    }
    
    # MAGICZNA LINIJKA DLA IDM/LDAP/PAM
    if use_enterprise_auth:
        config['auth_plugin'] = 'mysql_clear_password'
        # W niektórych konfiguracjach Enterprise wymagane jest też wyłączenie SSL check
        # lub wskazanie certyfikatu, ale 'mysql_clear_password' to 90% sukcesu.
    
    return mysql.connector.connect(**config)

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
    db_user = st.text_input("Your Username (e.g. j.kowalski)", value="")
    db_pass = st.text_input("Your Password", type="password")
    
    # NOWA OPCJA
    enterprise_auth = st.checkbox("Enterprise Auth (LDAP/PAM/IDM)", value=False, help="Check this if you use Active Directory/LDAP credentials to login.")
    
    if st.button("Test Connection"):
        try:
            conn = get_db_connection(db_host, db_port, db_user, db_pass, enterprise_auth)
            if conn.is_connected():
                st.success(f"Connected to {db_host} as {db_user} successfully!")
                conn.close()
        except Error as e:
            st.error(f"Connection Failed: {e}")
        except ValueError:
            st.error("Port must be a number!")

# Main Section
st.header("1. Upload Project Definitions")
uploaded_file = st.file_uploader("Select Excel File", type=['xlsx'])

if uploaded_file is not None and db_pass:
    df = pd.read_excel(uploaded_file)
    st.dataframe(df.head())
    
    col1, col2 = st.columns(2)
    dry_run = col1.checkbox("Simulation Mode (Dry Run)", value=True)
    
    if st.button("🚀 RUN PROVISIONING", type="primary"):
        if os.path.exists("DIST_TEMP"):
            shutil.rmtree("DIST_TEMP")
        os.makedirs("DIST_TEMP")
        
        progress_bar = st.progress(0)
        master_list = []
        logs = []
        
        total_rows = len(df)
        
        for index, row in df.iterrows():
            project = row['Project_Name']
            env = row['Environment']
            roles = [r.strip() for r in row['Roles'].split(',')]
            db_name = f"{project.lower()}_{env.lower()}"
            
            # SQL Logic
            sql_commands = []
            sql_commands.append(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4;")
            
            project_users = []
            
            for role in roles:
                username = f"{project.lower()}_{env.lower()}_{role.lower()}"
                password = generate_password()
                privileges = get_privileges_by_role(role)
                
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
            
            # Execution
            if not dry_run:
                try:
                    # Używamy nowej funkcji z obsługą auth_plugin
                    conn = get_db_connection(db_host, db_port, db_user, db_pass, enterprise_auth)
                    cursor = conn.cursor()
                    for sql in sql_commands:
                        cursor.execute(sql)
                    conn.commit()
                    conn.close()
                    logs.append(f"✅ {project}: Configured on port {db_port}.")
                except Error as e:
                    logs.append(f"❌ {project}: SQL Error - {e}")
            else:
                logs.append(f"ℹ️ {project}: Simulation OK.")
            
            create_local_files(project, env, project_users, db_host, db_port)
            progress_bar.progress((index + 1) / total_rows)

        st.success("Provisioning Completed!")
        for log in logs:
            st.text(log)
            
        master_df = pd.DataFrame(master_list)
        master_df.to_excel(os.path.join("DIST_TEMP", "MASTER_PASSWORDS_SECURE.xlsx"), index=False)
        
        with open(os.path.join("DIST_TEMP", "MASTER_PASSWORDS_SECURE.xlsx"), "rb") as f:
            st.download_button("📥 Download Secure Master Report", f, file_name="Master_Credentials.xlsx")
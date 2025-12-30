import logging
import re
import secrets
import string
import os
import mysql.connector
import pyzipper
from datetime import datetime

# --- CONFIGURATION ---
logging.basicConfig(
    filename='audit_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_audit(message, level="INFO"):
    """Logs an audit event to the file."""
    if level.upper() == "ERROR":
        logging.error(message)
    elif level.upper() == "WARNING":
        logging.warning(message)
    else:
        logging.info(message)

def compress_and_encrypt(file_path, password):
    """
    Compresses a file into an encrypted ZIP (AES-256).
    Returns the path to the new ZIP file.
    """
    base_name = os.path.basename(file_path)
    zip_path = file_path.replace(".xlsx", ".zip")
    
    # Ensure usage of bytes for password
    pwd_bytes = password.encode('utf-8')
    
    with pyzipper.AESZipFile(zip_path, 'w', compression=pyzipper.ZIP_LZMA, encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(pwd_bytes)
        zf.write(file_path, base_name)
        
    return zip_path


# --- SECURITY LOGIC (RBAC) ---
def get_privileges_by_role(role_name):
    """
    Maps the business role (from Excel) to specific MySQL Privileges.
    Implements the Principle of Least Privilege (PoLP).
    """
    role_upper = str(role_name).upper().strip()
    
    # 1. ADMINS / OWNERS (Full Control)
    if role_upper in ['DBO', 'ADMIN', 'OWNER', 'MIGRATOR']:
        return "ALL PRIVILEGES"
    
    # 2. READ ONLY (Reporting, Analytics) - Changed primary role to READ
    elif role_upper in ['READ', 'READER', 'RO', 'REPORT', 'ANALYTICS']:
        return "SELECT"
    
    # 3. STANDARD APP / BATCH (Data Manipulation - No DDL)
    else:
        return "SELECT, INSERT, UPDATE, DELETE, EXECUTE, SHOW VIEW"

# --- HELPER FUNCTIONS ---
def validate_identifier(name):
    """Validates that a string contains only alphanumeric characters and underscores."""
    if not isinstance(name, str):
        name = str(name)
    
    if not re.match(r'^[a-zA-Z0-9_]+$', name):
        raise ValueError(f"Invalid identifier: '{name}'. Only alphanumeric characters and underscores are allowed to prevent SQL Injection.")
    return name

def generate_password(length=20):
    """Generates a cryptographically secure, random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        if (any(c.islower() for c in password) 
                and any(c.isupper() for c in password) 
                and sum(c.isdigit() for c in password) >= 3):
            return password

def create_local_files(project_name, env, users_data, db_host, db_port):
    """Generates folder structure and .env files locally for distribution."""
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
    """
    Handles database connection. 
    Supports standard auth and Enterprise Auth (LDAP/PAM) via mysql_clear_password.
    """
    config = {
        'host': host,
        'port': int(port),
        'user': user,
        'password': password,
        'connect_timeout': 10
    }
    
    # Key configuration for IDM/LDAP/PAM authentication
    if use_enterprise_auth:
        config['auth_plugin'] = 'mysql_clear_password'
    
    return mysql.connector.connect(**config)

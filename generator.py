import pandas as pd
import secrets
import string
import os
from datetime import datetime
import mysql.connector
from mysql.connector import Error

# --- KONFIGURACJA (UZUPEŁNIJ SWOJE DANE) ---
DB_HOST = '192.168.100.101'       
DB_ADMIN_USER = 'tester_admin'      
DB_ADMIN_PASS = 'haslo_testera'  # <--- WPISZ SWOJE HASŁO
INPUT_FILE = 'input_projects.xlsx'

# ZMIENIAMY NA FALSE = TERAZ DZIAŁAMY NA SERIO
DRY_RUN = False 

def generate_password(length=20):
    """Generuje bezpieczne hasło."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and sum(c.isdigit() for c in password) >= 3):
            return password

def create_environment_structure(project_name, env, users_data):
    """Tworzy strukturę folderów i pliki .env w folderze DIST."""
    folder_name = f"{project_name}_{env}"
    base_path = os.path.join("DIST", folder_name)
    os.makedirs(base_path, exist_ok=True)
    
    env_content = f"# Auto-generated config for {project_name} ({env})\n"
    env_content += f"# Generated on: {datetime.now()}\n"
    env_content += f"DB_HOST={DB_HOST}\n"
    
    # Dodajemy zmienną z nazwą bazy (standardowo nazwa_projektu_srodowisko)
    db_name = f"{project_name.lower()}_{env.lower()}"
    env_content += f"DB_NAME={db_name}\n\n"
    
    for user in users_data:
        role = user['role'].upper()
        env_content += f"# Role: {role}\n"
        env_content += f"DB_USER_{role}={user['user']}\n"
        env_content += f"DB_PASS_{role}={user['password']}\n"
    
    with open(os.path.join(base_path, ".env"), "w") as f:
        f.write(env_content)

def execute_sql(commands):
    """Łączy się z bazą i wykonuje listę komend SQL."""
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_ADMIN_USER,
            password=DB_ADMIN_PASS
        )
        if conn.is_connected():
            cursor = conn.cursor()
            for sql in commands:
                try:
                    cursor.execute(sql)
                    print(f" [SQL OK] {sql[:60]}...") 
                except Error as e:
                    print(f" [SQL ERROR] {e} przy komendzie: {sql}")
            conn.commit()
    except Error as e:
        print(f" [CONNECTION ERROR] Nie można połączyć z MySQL: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def main():
    print(f"--- START AUTOMATYZACJI (DRY_RUN: {DRY_RUN}) ---")
    
    try:
        df = pd.read_excel(INPUT_FILE)
    except FileNotFoundError:
        print(f"BŁĄD: Nie znaleziono pliku {INPUT_FILE}. Utwórz go najpierw.")
        return

    master_list = []
    today_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
    
    # Tworzymy główny katalog wyjściowy
    if not os.path.exists("DIST"):
        os.mkdir("DIST")

    for index, row in df.iterrows():
        project = row['Project_Name']
        env = row['Environment']
        roles = [r.strip() for r in row['Roles'].split(',')]
        
        db_name = f"{project.lower()}_{env.lower()}"
        
        print(f"\n>>> Projekt: {project} [{env}] | Baza: {db_name}")
        
        project_users = []
        sql_commands_batch = []
        
        # 1. Najpierw tworzymy bazę danych (jeśli nie istnieje)
        create_db_sql = f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        sql_commands_batch.append(create_db_sql)

        # 2. Generowanie userów
        for role in roles:
            username = f"{project.lower()}_{env.lower()}_{role.lower()}"
            password = generate_password()
            
            # Używamy IF NOT EXISTS żeby skrypt się nie wywalił przy ponownym uruchomieniu
            create_user_sql = f"CREATE USER IF NOT EXISTS '{username}'@'%' IDENTIFIED BY '{password}';"
            # Jeśli user istnieje, to ALTER zmienia hasło na nowe (opcjonalne, ale przydatne)
            alter_user_sql = f"ALTER USER '{username}'@'%' IDENTIFIED BY '{password}';"
            
            grant_sql = f"GRANT ALL PRIVILEGES ON {db_name}.* TO '{username}'@'%';"
            
            sql_commands_batch.append(create_user_sql)
            sql_commands_batch.append(alter_user_sql) 
            sql_commands_batch.append(grant_sql)
            
            user_info = {
                'project': project,
                'env': env,
                'role': role,
                'user': username,
                'password': password,
                'host': DB_HOST
            }
            master_list.append(user_info)
            project_users.append(user_info)

        sql_commands_batch.append("FLUSH PRIVILEGES;")

        # Wykonanie SQL (Tylko jeśli nie DRY_RUN)
        if not DRY_RUN:
            execute_sql(sql_commands_batch)
        else:
            print(" [INFO] Tryb symulacji - SQL nie został wysłany do bazy.")

        # 3. Zapis plików na dysk
        create_environment_structure(project, env, project_users)

    # 4. Raport Master
    master_df = pd.DataFrame(master_list)
    master_filename = f"MASTER_PASSWORDS_{today_str}.xlsx"
    master_df.to_excel(master_filename, index=False)
    
    print(f"\n--- ZAKOŃCZONO ---")
    print(f"Raport zbiorczy: {master_filename}")

if __name__ == "__main__":
    main()
# 🛡️ Enterprise MySQL Provisioning Tool

A professional "Infrastructure as Code" (IaC) solution for automating database provisioning, user management, and access control compliance. Designed for high-security environments (Bank/FinTech).

## 🚀 Key Features

### 1. Security & Compliance (RBAC)
Implements **Role-Based Access Control** based on the Principle of Least Privilege:
* **DBO/Admin:** Full access (`ALL PRIVILEGES`).
* **App/Batch:** Data manipulation only (`SELECT`, `INSERT`, `UPDATE`, `DELETE`, `EXECUTE`).
* **READ/Analytics:** Read-only access (`SELECT`).

### 2. Enterprise Authentication
* Supports standard native authentication.
* **LDAP/PAM/IDM Support:** Includes `mysql_clear_password` plugin support for corporate directory integration (Active Directory).

### 3. Hybrid Output
Generates two sets of deliverables per run:
* **For Admins:** A Master Excel Report containing all credentials, hosts, and assigned privileges.
* **For Developers:** Ready-to-use `.env` configuration files (including `DB_HOST`, `DB_PORT`, `DB_NAME`).

### 4. Advanced Connectivity
* Support for **Custom Ports** (essential for multi-instance servers).
* Remote and Local provisioning capabilities.

## 🛠 Tech Stack
* **Core:** Python 3.9+
* **UI:** Streamlit (No-Code interface for Ops teams)
* **Database:** MySQL Connector (w/ Enterprise Auth support)
* **Data:** Pandas (Excel processing)

## 📸 Usage Workflow
1. **Upload Projects:** Drag & drop an Excel file with columns: `Project_Name`, `Environment`, `Roles`.
2. **Configure Connection:** Set Host, Port, and authenticate via Root or LDAP credentials in the Sidebar.
3. **Run Provisioning:** The tool executes idempotent SQL commands (`CREATE IF NOT EXISTS`, `ALTER USER`) to ensure safe re-runs.
4. **Distribute:** Download the secured Master Report and distribute generated `.env` files to dev teams.

## 📊 Input File Structure
The application requires an Excel file (`.xlsx`) with exactly three columns.

**Required Headers:**
* `Project_Name`: Name of the service/db (e.g. `ECommerce`)
* `Environment`: Target env (e.g. `PROD`, `DEV`)
* `Roles`: Comma-separated list of roles (e.g. `app, dbo, read`)

**Example Data:**

| Project_Name | Environment | Roles |
| :--- | :--- | :--- |
| MyApp | PROD | app, dbo, read |
| AnalyticsDB | STAGE | report, analytics |
| LegacySystem | DEV | owner, migrator |

> 💡 **Tip:** You can download the [example_input.xlsx](example_input.xlsx) file from this repository to get started quickly.
---
*Author: Kacper Luźniak*
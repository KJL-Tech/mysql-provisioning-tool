# 🐬 MySQL Provisioning Automator

An "Infrastructure as Code" (IaC) tool for bulk management of MySQL users and permissions, featuring a modern Streamlit-based GUI.

## 🚀 Key Features
* **Security First:** Automatically generates cryptographically strong passwords (20 chars, mixed case, special chars).
* **Hybrid Output:** Generates a **Master Report** for Administrators (Excel) and ready-to-use **.env configuration files** for Developer teams.
* **Idempotency:** Safe to run multiple times. The script handles existing users (updates passwords/grants) without throwing errors.
* **User-Friendly GUI:** No CLI knowledge required. Just drag & drop your requirements.

## 🛠 Tech Stack
* **Core:** Python 3.9+
* **Database:** MySQL Connector
* **Data Processing:** Pandas
* **UI:** Streamlit

## 💡 The Problem Solved
In Enterprise environments, manually provisioning users for multiple microservices (Dev/Test/Prod) is time-consuming and error-prone. This tool reduces the process to 30 seconds, ensuring full compliance with security policies (RBAC).

## 📸 How to use
1. Upload an Excel file with project definitions (`Project_Name`, `Environment`, `Roles`).
2. Configure the database connection in the sidebar (supports Local & Remote).
3. Click "Run Provisioning" - the tool executes SQL commands and generates deployment packages.

---
*Author: Kacper Luźniak
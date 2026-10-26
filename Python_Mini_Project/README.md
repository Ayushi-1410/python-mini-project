# Smart Patient Queue and Emergency Prioritization System

A college demonstration project using Flask, MySQL, HTML, CSS, and vanilla JavaScript. Staff choose priority categories; the system does not diagnose patients or perform clinical triage.

## Setup

Activate the existing Windows virtual environment from PowerShell in the project folder:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies if needed:

```powershell
python -m pip install -r requirements.txt
```

The authentication and CSRF features use Flask's existing Werkzeug dependency; no additional Python package is required. Configure MySQL and `FLASK_SECRET_KEY` in the private `.env` file. The database name should be `python_mini_project`. Keep `.env` private; it is excluded by `.gitignore`. Replace the secret placeholder with a unique random value and do not commit it.

## Database migration

The existing `patients` table is not dropped, recreated, or altered. Run the additive staff-account migration once:

1. Open MySQL Workbench and connect to the server used by the application.
2. Choose **File > Open SQL Script** and open `database/migrate_staff_accounts.sql`.
3. Execute the script with the lightning-bolt button. It creates only `staff_accounts` using `CREATE TABLE IF NOT EXISTS`.
4. Refresh the `python_mini_project` schema in the SCHEMAS panel and confirm that `staff_accounts` appears. Existing patient rows remain untouched.

The full `database/schema.sql` also contains this additive staff table definition for a fresh setup.

## Start and use

From the project folder, with the virtual environment activated and MySQL running:

```powershell
python app.py
```

- Login: <http://127.0.0.1:5000/login>
- Staff registration: <http://127.0.0.1:5000/register>
- Dashboard: <http://127.0.0.1:5000/dashboard>

Create a staff account, log in, then register a test patient. The queue supports department filtering and partial patient ID/name search. Status changes and logout use POST forms with CSRF tokens. Stop Flask with `Ctrl+C`.

Do not enter real patient information. This student demonstration does not include account invitation/approval, rate limiting, audit history, or production health-data safeguards.

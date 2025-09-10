Medical Reports Full (Flask + SQLite) - Demo
-------------------------------------------

Run locally:
1. python3 -m venv venv
2. source venv/bin/activate   (Windows: venv\Scripts\activate)
3. pip install -r requirements.txt
4. flask run   (or python app.py)
Open http://127.0.0.1:5000/

Logins:
- Patient: Reg No (e.g. APO1001) and Password = first4letters(name)+DDMMYYYY
- Hospital Admins: username = hospital code (APO, FOR, AII, MED, MAX), password = admin123
- Super Admin: username = superadmin, password = super123

Files:
- app.py, config.py, requirements.txt
- data.db (SQLite) with hospitals, patients, admins, reports
- uploads/ (PDF reports)
- templates/, static/, sample_credentials.xlsx, README.md
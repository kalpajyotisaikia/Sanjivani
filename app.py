from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash, g
import os, sqlite3
from werkzeug.utils import secure_filename
from datetime import datetime
import config

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Patient login
@app.route('/', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        reg_no = request.form.get('reg_no','').strip()
        password = request.form.get('password','').strip()
        db = get_db()
        cur = db.execute("SELECT * FROM patients WHERE reg_no = ?", (reg_no,))
        patient = cur.fetchone()
        if patient:
            name = patient['name']
            dob = patient['dob']
            expected = (name[:4].lower() + datetime.strptime(dob, "%Y-%m-%d").strftime("%d%m%Y"))
            if password == expected:
                session['patient_id'] = patient['patient_id']
                session['patient_name'] = patient['name']
                # redirect to the hospital reports page for this patient
                return redirect(url_for('hospital_reports', hospital_id=patient['hospital_id']))
        flash("Invalid credentials", "danger")
    return render_template('login_modern.html')

# Hospital admin login
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username','').strip().upper()
        password = request.form.get('password','').strip()
        db = get_db()
        cur = db.execute("SELECT * FROM hospital_admins WHERE username = ? AND password = ?", (username, password))
        admin = cur.fetchone()
        if admin:
            session['admin_id'] = admin['admin_id']
            session['admin_username'] = admin['username']
            session['admin_hospital_id'] = admin['hospital_id']
            return redirect(url_for('admin_dashboard'))
        flash("Invalid admin credentials", "danger")
    return render_template('admin_login.html')

# Super admin login
@app.route('/super/login', methods=['GET','POST'])
def super_login():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','').strip()
        db = get_db()
        cur = db.execute("SELECT * FROM superadmins WHERE username = ? AND password = ?", (username, password))
        sa = cur.fetchone()
        if sa:
            session['super_id'] = sa['id']
            session['super_username'] = sa['username']
            return redirect(url_for('super_dashboard'))
        flash("Invalid super admin credentials", "danger")
    return render_template('super_login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Patient view: reports at hospital
@app.route('/hospital/<int:hospital_id>')
def hospital_reports(hospital_id):
    if 'patient_id' not in session:
        return redirect(url_for('login'))
    patient_id = session['patient_id']
    db = get_db()
    sql = "SELECT r.*, h.hospital_name FROM reports r JOIN hospitals h ON r.hospital_id = h.hospital_id WHERE r.patient_id = ? AND r.hospital_id = ? ORDER BY r.uploaded_at DESC"
    cur = db.execute(sql, (patient_id, hospital_id))
    reports = cur.fetchall()
    hcur = db.execute("SELECT * FROM hospitals WHERE hospital_id = ?", (hospital_id,))
    hospital = hcur.fetchone()
    return render_template('reports_modern.html', reports=reports, hospital=hospital)

# Admin dashboard for hospital admins
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    hid = session['admin_hospital_id']
    db = get_db()
    patients = db.execute("SELECT * FROM patients WHERE hospital_id = ? ORDER BY name", (hid,)).fetchall()
    reports = db.execute("SELECT r.*, p.name as patient_name FROM reports r JOIN patients p ON r.patient_id = p.patient_id WHERE r.hospital_id = ? ORDER BY r.uploaded_at DESC", (hid,)).fetchall()
    return render_template('admin_dashboard.html', patients=patients, reports=reports)

# Super admin dashboard
@app.route('/super/dashboard')
def super_dashboard():
    if 'super_id' not in session:
        return redirect(url_for('super_login'))
    db = get_db()
    stats = {}
    stats['hospitals'] = db.execute("SELECT COUNT(*) as c FROM hospitals").fetchone()['c']
    stats['patients'] = db.execute("SELECT COUNT(*) as c FROM patients").fetchone()['c']
    stats['reports'] = db.execute("SELECT COUNT(*) as c FROM reports").fetchone()['c']
    hospitals = db.execute("SELECT * FROM hospitals").fetchall()
    return render_template('super_dashboard.html', stats=stats, hospitals=hospitals)

# Download report
@app.route('/download/<path:filename>')
def download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# Upload (used by admin)
@app.route('/admin/upload', methods=['GET','POST'])
def admin_upload():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    db = get_db()
    hid = session['admin_hospital_id']
    hospitals = db.execute("SELECT * FROM hospitals ORDER BY hospital_name").fetchall()
    if request.method == 'POST':
        reg_no = request.form.get('reg_no','').strip()
        report_type = request.form.get('report_type','').strip()
        file = request.files.get('file')
        if not (reg_no and report_type and file):
            flash("All fields required", "warning")
            return redirect(url_for('admin_upload'))
        if not allowed_file(file.filename):
            flash("File type not allowed", "warning")
            return redirect(url_for('admin_upload'))
        cur = db.execute("SELECT patient_id FROM patients WHERE reg_no = ?", (reg_no,))
        patient = cur.fetchone()
        if not patient:
            flash("Patient not found", "danger")
            return redirect(url_for('admin_upload'))
        filename = secure_filename(f"{reg_no}_{hid}_{int(datetime.utcnow().timestamp())}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        db.execute("INSERT INTO reports (patient_id, hospital_id,report_type, file_path, uploaded_at) VALUES (?,?,?,?,?)",
                   (patient['patient_id'], hid, report_type, filename, datetime.datetime.utcnow().isoformat()))
        db.commit()
        flash("Uploaded successfully", "success")
        return redirect(url_for('admin_upload'))
    return render_template('upload_modern.html', hospitals=hospitals)

# Delete report (admin)
@app.route('/admin/delete_report/<int:report_id>', methods=['POST'])
def delete_report(report_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    db = get_db()
    r = db.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,)).fetchone()
    if r:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], r['file_path']))
        except Exception:
            pass
        db.execute("DELETE FROM reports WHERE report_id = ?", (report_id,))
        db.commit()
        flash("Report deleted", "success")
    return redirect(url_for('admin_dashboard'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

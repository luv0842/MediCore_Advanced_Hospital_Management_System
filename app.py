import os
from functools import wraps
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from dotenv import load_dotenv
import mysql.connector

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "replace-this-secret-in-production")
app.config.update(
    MAIL_SERVER="smtp.gmail.com", MAIL_PORT=587, MAIL_USE_TLS=True,
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_DEFAULT_SENDER=os.getenv("MAIL_USERNAME")
)
mail = Mail(app)

def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="luv_goswami",
        password="MediCore@123",
        database="medicore_hms"
    )

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped

def roles_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if session.get("role") not in roles:
                flash("You do not have permission to access this module.", "danger")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapped
    return deco

def email_patient(to, subject, body):
    if not to or not app.config.get("MAIL_USERNAME") or not app.config.get("MAIL_PASSWORD"):
        return False
    try:
        mail.send(Message(subject=subject, recipients=[to], body=body))
        return True
    except Exception:
        app.logger.exception("Email delivery failed")
        return False

@app.route("/")
def index():
    return redirect(url_for("dashboard") if session.get("user_id") else url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        conn = connect_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email=%s AND is_active=1", (request.form["email"].strip(),))
        user = cur.fetchone()
        cur.close(); conn.close()
        if user and check_password_hash(user["password_hash"], request.form["password"]):
            session.update(user_id=user["id"], name=user["full_name"], role=user["role"])
            return redirect(url_for("dashboard"))
        flash("Incorrect email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    conn = connect_db(); cur = conn.cursor(dictionary=True)
    queries = {
        "patients": "SELECT COUNT(*) n FROM patients",
        "doctors": "SELECT COUNT(*) n FROM doctors",
        "appointments": "SELECT COUNT(*) n FROM appointments WHERE appointment_date=CURDATE()",
        "revenue": "SELECT COALESCE(SUM(amount),0) n FROM bills WHERE payment_status='Paid' AND MONTH(created_at)=MONTH(CURDATE()) AND YEAR(created_at)=YEAR(CURDATE())",
        "pending": "SELECT COUNT(*) n FROM appointments WHERE status='Scheduled'"
    }
    stats = {}
    for key, sql in queries.items():
        cur.execute(sql); stats[key] = cur.fetchone()["n"]
    cur.execute("""SELECT a.id,p.full_name patient,d.full_name doctor,a.appointment_date,
                   a.appointment_time,a.status FROM appointments a
                   JOIN patients p ON p.id=a.patient_id JOIN doctors d ON d.id=a.doctor_id
                   ORDER BY a.appointment_date DESC,a.appointment_time DESC LIMIT 7""")
    recent = cur.fetchall()
    cur.close(); conn.close()
    return render_template("dashboard.html", stats=stats, recent=recent)

@app.route("/patients", methods=["GET", "POST"])
@login_required
def patients():
    conn = connect_db(); cur = conn.cursor(dictionary=True)
    if request.method == "POST":
        cur.execute("""INSERT INTO patients(full_name,email,phone,gender,date_of_birth,blood_group,address)
                       VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                    (request.form["full_name"], request.form.get("email"), request.form.get("phone"),
                     request.form.get("gender"), request.form.get("date_of_birth") or None,
                     request.form.get("blood_group"), request.form.get("address")))
        conn.commit()
        email_patient(request.form.get("email"), "Welcome to MediCore Hospital",
                      f"Hello {request.form['full_name']}, your patient registration has been completed.")
        flash("Patient record created successfully.", "success")
        cur.close(); conn.close()
        return redirect(url_for("patients"))
    cur.execute("SELECT * FROM patients ORDER BY created_at DESC")
    rows = cur.fetchall(); cur.close(); conn.close()
    return render_template("patients.html", patients=rows)

@app.route("/doctors", methods=["GET", "POST"])
@login_required
def doctors():
    conn = connect_db(); cur = conn.cursor(dictionary=True)
    if request.method == "POST":
        cur.execute("""INSERT INTO doctors(full_name,email,phone,specialization,consultation_fee)
                       VALUES(%s,%s,%s,%s,%s)""",
                    (request.form["full_name"], request.form.get("email"), request.form.get("phone"),
                     request.form.get("specialization"), request.form.get("consultation_fee") or 0))
        conn.commit(); flash("Doctor added successfully.", "success")
        cur.close(); conn.close()
        return redirect(url_for("doctors"))
    cur.execute("SELECT * FROM doctors ORDER BY full_name")
    rows = cur.fetchall(); cur.close(); conn.close()
    return render_template("doctors.html", doctors=rows)

@app.route("/appointments", methods=["GET", "POST"])
@login_required
def appointments():
    conn = connect_db(); cur = conn.cursor(dictionary=True)
    if request.method == "POST":
        cur.execute("""INSERT INTO appointments(patient_id,doctor_id,appointment_date,appointment_time,reason)
                       VALUES(%s,%s,%s,%s,%s)""",
                    (request.form["patient_id"], request.form["doctor_id"], request.form["appointment_date"],
                     request.form["appointment_time"], request.form.get("reason")))
        conn.commit()
        cur.execute("SELECT full_name,email FROM patients WHERE id=%s", (request.form["patient_id"],))
        p = cur.fetchone()
        sent = email_patient(p["email"] if p else None, "Appointment confirmed",
             f"Hello {p['full_name'] if p else ''}, your appointment is scheduled for {request.form['appointment_date']} at {request.form['appointment_time']}.")
        flash("Appointment booked. Email notification " + ("sent." if sent else "not sent (check SMTP settings or patient email)."), "success")
        cur.close(); conn.close()
        return redirect(url_for("appointments"))
    cur.execute("SELECT id,full_name FROM patients ORDER BY full_name"); patient_rows = cur.fetchall()
    cur.execute("SELECT id,full_name,specialization FROM doctors ORDER BY full_name"); doctor_rows = cur.fetchall()
    cur.execute("""SELECT a.*,p.full_name patient,d.full_name doctor FROM appointments a
                   JOIN patients p ON p.id=a.patient_id JOIN doctors d ON d.id=a.doctor_id
                   ORDER BY a.appointment_date DESC,a.appointment_time DESC""")
    rows = cur.fetchall(); cur.close(); conn.close()
    return render_template("appointments.html", appointments=rows, patients=patient_rows, doctors=doctor_rows)

@app.route("/appointments/<int:appointment_id>/status", methods=["POST"])
@login_required
def appointment_status(appointment_id):
    status = request.form.get("status")
    if status not in ("Scheduled", "Completed", "Cancelled", "No-show"):
        flash("Invalid appointment status.", "danger")
    else:
        conn = connect_db(); cur = conn.cursor()
        cur.execute("UPDATE appointments SET status=%s WHERE id=%s", (status, appointment_id))
        conn.commit(); cur.close(); conn.close()
        flash("Appointment status updated.", "success")
    return redirect(url_for("appointments"))

@app.route("/billing", methods=["GET", "POST"])
@login_required
def billing():
    conn = connect_db(); cur = conn.cursor(dictionary=True)
    if request.method == "POST":
        cur.execute("INSERT INTO bills(patient_id,description,amount,payment_status) VALUES(%s,%s,%s,%s)",
                    (request.form["patient_id"], request.form.get("description"),
                     request.form["amount"], request.form.get("payment_status", "Unpaid")))
        conn.commit(); flash("Bill created successfully.", "success")
        cur.close(); conn.close()
        return redirect(url_for("billing"))
    cur.execute("SELECT id,full_name FROM patients ORDER BY full_name"); patient_rows = cur.fetchall()
    cur.execute("""SELECT b.*,p.full_name patient FROM bills b JOIN patients p ON p.id=b.patient_id
                   ORDER BY b.created_at DESC"""); rows = cur.fetchall()
    cur.close(); conn.close()
    return render_template("billing.html", bills=rows, patients=patient_rows)

@app.route("/pharmacy", methods=["GET", "POST"])
@login_required
def pharmacy():
    conn = connect_db(); cur = conn.cursor(dictionary=True)
    if request.method == "POST":
        cur.execute("""INSERT INTO medicines(medicine_name,category,quantity,unit_price,expiry_date)
                       VALUES(%s,%s,%s,%s,%s)""",
                    (request.form["medicine_name"], request.form.get("category"),
                     request.form["quantity"], request.form["unit_price"],
                     request.form.get("expiry_date") or None))
        conn.commit(); flash("Medicine inventory updated.", "success")
        cur.close(); conn.close()
        return redirect(url_for("pharmacy"))
    cur.execute("SELECT * FROM medicines ORDER BY medicine_name"); rows = cur.fetchall()
    cur.close(); conn.close()
    return render_template("pharmacy.html", medicines=rows)

@app.route("/laboratory", methods=["GET", "POST"])
@login_required
def laboratory():
    conn = connect_db(); cur = conn.cursor(dictionary=True)
    if request.method == "POST":
        cur.execute("""INSERT INTO lab_tests(patient_id,test_name,test_date,result,status)
                       VALUES(%s,%s,%s,%s,%s)""",
                    (request.form["patient_id"], request.form["test_name"],
                     request.form.get("test_date") or date.today().isoformat(),
                     request.form.get("result"), request.form.get("status", "Pending")))
        conn.commit(); flash("Laboratory test added.", "success")
        cur.close(); conn.close()
        return redirect(url_for("laboratory"))
    cur.execute("SELECT id,full_name FROM patients ORDER BY full_name"); patient_rows = cur.fetchall()
    cur.execute("""SELECT l.*,p.full_name patient FROM lab_tests l JOIN patients p ON p.id=l.patient_id
                   ORDER BY l.test_date DESC"""); rows = cur.fetchall()
    cur.close(); conn.close()
    return render_template("laboratory.html", tests=rows, patients=patient_rows)

@app.route("/reports")
@login_required
def reports():
    conn = connect_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) total FROM patients"); total_patients = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) total FROM appointments WHERE MONTH(appointment_date)=MONTH(CURDATE()) AND YEAR(appointment_date)=YEAR(CURDATE())")
    monthly_appointments = cur.fetchone()["total"]
    cur.execute("SELECT COALESCE(SUM(amount),0) total FROM bills WHERE payment_status='Paid'")
    revenue = cur.fetchone()["total"]
    cur.close(); conn.close()
    return render_template("reports.html", total_patients=total_patients,
                           monthly_appointments=monthly_appointments, revenue=revenue)

if __name__ == "__main__":
    app.run(debug=True)

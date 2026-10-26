import hmac
import re
import secrets
from functools import wraps

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config, get_db_connection

app = Flask(__name__)
app.config.from_object(Config)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

DEPARTMENTS = ("General Medicine", "Pediatrics", "Orthopedics", "Cardiology")
GENDERS = ("Female", "Male", "Other", "Prefer not to say")
PRIORITIES = ("Emergency", "Urgent", "Normal")
PATIENT_STATUSES = ("Waiting", "In Consultation", "Completed")


@app.before_request
def protect_post_requests():
    token = session.setdefault("_csrf_token", secrets.token_urlsafe(32))
    if request.method == "POST":
        submitted_token = request.form.get("csrf_token", "")
        if not submitted_token or not hmac.compare_digest(token, submitted_token):
            abort(400, description="The form expired or could not be verified. Reload the page and try again.")


@app.context_processor
def inject_template_context():
    return {
        "csrf_token": session.get("_csrf_token", ""),
        "current_staff": session.get("staff_username"),
    }


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "staff_id" not in session:
            flash("Please log in to access the patient dashboard.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


@app.route("/")
def index():
    if "staff_id" in session:
        return redirect(url_for("home"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "staff_id" in session:
        return redirect(url_for("home"))
    if request.method == "GET":
        return render_template("login.html")

    identity = request.form.get("identity", "").strip().lower()
    password = request.form.get("password", "")
    if not identity or not password:
        return render_template("login.html", error="Enter your email or username and password.", identity=identity), 400

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT staff_id, username, email, password_hash FROM staff_accounts "
            "WHERE email = %s OR username = %s LIMIT 1",
            (identity, identity),
        )
        account = cursor.fetchone()
        if account is None or not check_password_hash(account["password_hash"], password):
            return render_template("login.html", error="The email/username or password is incorrect.", identity=identity), 401

        session.clear()
        session["staff_id"] = account["staff_id"]
        session["staff_username"] = account["username"]
        session["_csrf_token"] = secrets.token_urlsafe(32)
        return redirect(url_for("home"))
    except Error:
        app.logger.exception("Unable to authenticate staff account.")
        return render_template("login.html", error="Sign in is temporarily unavailable. Check the database setup."), 503
    finally:
        _close_database_resources(cursor, connection)


@app.route("/register", methods=["GET", "POST"])
def register():
    if "staff_id" in session:
        return redirect(url_for("home"))
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username", "").strip().lower()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    password_confirm = request.form.get("password_confirm", "")
    errors = {}

    if not re.fullmatch(r"[a-zA-Z0-9_.-]{3,50}", username):
        errors["username"] = "Use 3-50 letters, numbers, dots, underscores, or hyphens."
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        errors["email"] = "Enter a valid email address."
    if len(password) < 10 or len(password) > 128:
        errors["password"] = "Password must be between 10 and 128 characters."
    if password != password_confirm:
        errors["password_confirm"] = "The passwords do not match."
    if errors:
        return render_template("register.html", errors=errors, username=username, email=email), 400

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT staff_id FROM staff_accounts WHERE username = %s OR email = %s LIMIT 1",
            (username, email),
        )
        if cursor.fetchone() is not None:
            return render_template(
                "register.html",
                errors={"account": "That username or email is already registered."},
                username=username,
                email=email,
            ), 409
        cursor.execute(
            "INSERT INTO staff_accounts (username, email, password_hash) VALUES (%s, %s, %s)",
            (username, email, generate_password_hash(password)),
        )
        connection.commit()
        flash("Staff account created. You can now log in.", "success")
        return redirect(url_for("login"))
    except Error as error:
        if connection is not None:
            connection.rollback()
        app.logger.exception("Unable to create staff account.")
        if error.errno == 1062:
            return render_template(
                "register.html",
                errors={"account": "That username or email is already registered."},
                username=username,
                email=email,
            ), 409
        return render_template("register.html", errors={"account": "Registration is temporarily unavailable."}), 503
    finally:
        _close_database_resources(cursor, connection)


@app.route("/dashboard")
@app.route("/patients", methods=["GET"])
@login_required
def home():
    """Render the dashboard and active queue, with optional filters."""
    department = request.args.get("department", "").strip()
    search = request.args.get("search", "").strip()
    errors = {}
    if department and department not in DEPARTMENTS:
        errors["department"] = "Select one of the listed departments."
        department = ""
    if len(search) > 100:
        errors["search"] = "Search must be 100 characters or fewer."
        search = search[:100]

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        patients = _fetch_active_patients(cursor, department=department, search=search)
        counts = _fetch_dashboard_counts(cursor)
        return render_template(
            "index.html",
            patients=patients,
            counts=counts,
            department=department,
            search=search,
            departments=DEPARTMENTS,
            filter_errors=errors,
            form_errors={},
            form_values={},
        ), (400 if errors else 200)
    except (Error, ValueError):
        app.logger.exception("Unable to load the active patient queue.")
        flash("The patient queue is temporarily unavailable.", "error")
        return render_template(
            "index.html",
            patients=[],
            counts=_empty_dashboard_counts(),
            department=department,
            search=search,
            departments=DEPARTMENTS,
            filter_errors=errors,
            form_errors={},
            form_values={},
        ), 503
    finally:
        _close_database_resources(cursor, connection)


def _fetch_active_patients(cursor, department="", search=""):
    conditions = ["status IN ('Waiting', 'In Consultation')"]
    parameters = []
    if department:
        conditions.append("department = %s")
        parameters.append(department)
    if search:
        conditions.append("(CAST(patient_id AS CHAR) LIKE %s OR patient_name LIKE %s)")
        parameters.extend((f"%{search}%", f"%{search}%"))
    cursor.execute(
        f"""
        SELECT patient_id, patient_name, age, gender, contact_number,
               department, symptoms, priority_level, queue_number, status,
               registered_at
        FROM patients
        WHERE {' AND '.join(conditions)}
        ORDER BY CASE priority_level
                     WHEN 'Emergency' THEN 1
                     WHEN 'Urgent' THEN 2
                     ELSE 3
                 END,
                 registered_at ASC,
                 patient_id ASC
        """,
        tuple(parameters),
    )
    return cursor.fetchall()


def _empty_dashboard_counts():
    return {
        "waiting": 0,
        "emergency": 0,
        "in_consultation": 0,
        "completed": 0,
        "active": 0,
    }


def _fetch_dashboard_counts(cursor):
    cursor.execute(
        """
        SELECT
            COALESCE(SUM(status = 'Waiting'), 0) AS waiting,
            COALESCE(SUM(priority_level = 'Emergency' AND status <> 'Completed'), 0) AS emergency,
            COALESCE(SUM(status = 'In Consultation'), 0) AS in_consultation,
            COALESCE(SUM(status = 'Completed'), 0) AS completed,
            COALESCE(SUM(status IN ('Waiting', 'In Consultation')), 0) AS active
        FROM patients
        """
    )
    return cursor.fetchone() or _empty_dashboard_counts()


def _close_database_resources(cursor, connection):
    try:
        if cursor is not None:
            cursor.close()
    except Error:
        app.logger.warning("Unable to close the database cursor.")
    try:
        if connection is not None and connection.is_connected():
            connection.close()
    except Error:
        app.logger.warning("Unable to close the database connection.")


def _validate_patient_form(form):
    patient_name = form.get("patient_name", "").strip()
    age_text = form.get("age", "").strip()
    gender = form.get("gender", "").strip()
    contact_number = form.get("contact_number", "").strip() or None
    department = form.get("department", "").strip()
    symptoms = form.get("symptoms", "").strip()
    priority_level = form.get("priority_level", "").strip()

    errors = {}
    if not patient_name or len(patient_name) > 100:
        errors["patient_name"] = "Patient name is required and must be at most 100 characters."
    try:
        age = int(age_text)
    except ValueError:
        age = None
        errors["age"] = "Age must be a whole number from 1 to 120."
    if age is not None and not 1 <= age <= 120:
        errors["age"] = "Age must be a whole number from 1 to 120."
    if gender not in GENDERS:
        errors["gender"] = "Select a supported gender option."
    if contact_number and (
        len(contact_number) > 30
        or not re.fullmatch(r"\+?[0-9() -]+", contact_number)
        or not 7 <= sum(character.isdigit() for character in contact_number) <= 15
    ):
        errors["contact_number"] = "Enter a valid contact number, or leave it blank."
    if department not in DEPARTMENTS:
        errors["department"] = "Select one of the listed departments."
    if not symptoms or len(symptoms) > 5000:
        errors["symptoms"] = "Reason for visit is required and must be at most 5000 characters."
    if priority_level not in PRIORITIES:
        errors["priority_level"] = "Select Emergency, Urgent, or Normal priority."
    if errors:
        return None, errors

    return {
        "patient_name": patient_name,
        "age": age,
        "gender": gender,
        "contact_number": contact_number,
        "department": department,
        "symptoms": symptoms,
        "priority_level": priority_level,
    }, {}


@app.route("/patients", methods=["POST"])
@login_required
def register_patient():
    """Validate and register a patient with an initial Waiting status."""
    patient, form_errors = _validate_patient_form(request.form)
    if form_errors:
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            patients = _fetch_active_patients(cursor)
            counts = _fetch_dashboard_counts(cursor)
            return render_template(
                "index.html",
                patients=patients,
                counts=counts,
                department="",
                search="",
                departments=DEPARTMENTS,
                filter_errors={},
                form_errors=form_errors,
                form_values=request.form,
            ), 400
        except Error:
            app.logger.exception("Unable to reload the dashboard after invalid patient input.")
            flash("Please correct the highlighted patient details.", "error")
            return redirect(url_for("home"))
        finally:
            _close_database_resources(cursor, connection)

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        connection.start_transaction()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO patients
                (patient_name, age, gender, contact_number, department,
                 symptoms, priority_level, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Waiting')
            """,
            (
                patient["patient_name"],
                patient["age"],
                patient["gender"],
                patient["contact_number"],
                patient["department"],
                patient["symptoms"],
                patient["priority_level"],
            ),
        )
        patient_id = cursor.lastrowid
        cursor.execute(
            "UPDATE patients SET queue_number = %s WHERE patient_id = %s",
            (patient_id, patient_id),
        )
        connection.commit()
        flash("Patient registered successfully.", "success")
    except (Error, ValueError):
        if connection is not None:
            connection.rollback()
        app.logger.exception("Unable to register patient.")
        flash("Patient registration failed. Check the database and try again.", "error")
    finally:
        _close_database_resources(cursor, connection)
    return redirect(url_for("home"))


@app.route("/patients/<int:patient_id>")
@login_required
def patient_details(patient_id):
    """Render the dashboard with one patient's details in its template context."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM patients WHERE patient_id = %s", (patient_id,))
        patient = cursor.fetchone()
        if patient is None:
            return "Patient not found.", 404
        patients = _fetch_active_patients(cursor)
        counts = _fetch_dashboard_counts(cursor)
        return render_template(
            "index.html", patients=patients, patient=patient, counts=counts,
            department="", search="", departments=DEPARTMENTS,
            filter_errors={}, form_errors={}, form_values={},
        )
    except (Error, ValueError):
        app.logger.exception("Unable to load patient details.")
        return "Patient details are temporarily unavailable.", 503
    finally:
        _close_database_resources(cursor, connection)


@app.route("/patients/<int:patient_id>/status", methods=["POST"])
@login_required
def update_patient_status(patient_id):
    """Update a patient's status to one of the supported values."""
    status = request.form.get("status", "").strip()
    if status not in PATIENT_STATUSES:
        flash("Select a valid patient status.", "error")
        return redirect(url_for("home"))

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE patients SET status = %s WHERE patient_id = %s",
            (status, patient_id),
        )
        if cursor.rowcount == 0:
            cursor.execute("SELECT patient_id FROM patients WHERE patient_id = %s", (patient_id,))
            if cursor.fetchone() is None:
                return "Patient not found.", 404
        connection.commit()
        flash("Patient status updated.", "success")
    except (Error, ValueError):
        if connection is not None:
            connection.rollback()
        app.logger.exception("Unable to update patient status.")
        flash("Patient status could not be updated.", "error")
    finally:
        _close_database_resources(cursor, connection)
    return redirect(url_for("home"))


@app.route("/patients/<int:patient_id>/delete", methods=["POST"])
@login_required
def remove_patient(patient_id):
    """Remove a patient only when requested through a POST submission."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM patients WHERE patient_id = %s", (patient_id,))
        if cursor.rowcount == 0:
            return "Patient not found.", 404
        connection.commit()
        flash("Patient removed from the system.", "success")
    except (Error, ValueError):
        if connection is not None:
            connection.rollback()
        app.logger.exception("Unable to remove patient.")
        flash("Patient could not be removed.", "error")
    finally:
        _close_database_resources(cursor, connection)
    return redirect(url_for("home"))


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)

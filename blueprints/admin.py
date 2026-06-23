from flask import Blueprint, render_template, request, redirect, url_for, flash

from db import query_all, query_one, execute
from decorators import role_required, get_current_user
from werkzeug.security import generate_password_hash
from blueprints.helpers import notify, recalc_project_progress

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@role_required("admin")
def dashboard():
    stats = {
        "employees": query_one("SELECT COUNT(*) c FROM users WHERE role='employee'")["c"],
        "team_leads": query_one("SELECT COUNT(*) c FROM users WHERE role='team_lead'")["c"],
        "clients": query_one("SELECT COUNT(*) c FROM users WHERE role='client'")["c"],
        "active_projects": query_one(
            "SELECT COUNT(*) c FROM projects WHERE status NOT IN ('Delivered')"
        )["c"],
        "delivered_projects": query_one(
            "SELECT COUNT(*) c FROM projects WHERE status='Delivered'"
        )["c"],
        "revenue": query_one(
            "SELECT COALESCE(SUM(amount),0) s FROM invoices WHERE status='Paid'"
        )["s"],
        "pending_revenue": query_one(
            "SELECT COALESCE(SUM(amount),0) s FROM invoices WHERE status!='Paid'"
        )["s"],
    }
    recent_projects = query_all(
        """SELECT p.*, u.name AS client_name FROM projects p
           JOIN users u ON u.id = p.client_id
           ORDER BY p.created_at DESC LIMIT 6"""
    )
    recent_contacts = query_all(
        "SELECT * FROM contact_messages ORDER BY created_at DESC LIMIT 5"
    )
    return render_template(
        "admin/dashboard.html", stats=stats, recent_projects=recent_projects,
        recent_contacts=recent_contacts,
    )


# ---------------------------------------------------------------- employees
@bp.route("/employees", methods=["GET", "POST"])
@role_required("admin")
def employees():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "employee")
        title = request.form.get("title", "").strip()

        errors = []
        if len(name) < 2:
            errors.append("Enter a full name.")
        if "@" not in email:
            errors.append("Enter a valid email.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if role not in ("employee", "team_lead"):
            errors.append("Invalid role.")
        if query_one("SELECT id FROM users WHERE email=?", (email,)):
            errors.append("That email is already registered.")

        if errors:
            for e in errors:
                flash(e, "error")
        else:
            execute(
                "INSERT INTO users (name, email, password_hash, role, title) "
                "VALUES (?, ?, ?, ?, ?)",
                (name, email, generate_password_hash(password), role, title),
            )
            flash(f"{name} added as {role.replace('_', ' ')}.", "success")
        return redirect(url_for("admin.employees"))

    staff = query_all(
        "SELECT * FROM users WHERE role IN ('employee','team_lead') ORDER BY role, name"
    )
    return render_template("admin/employees.html", staff=staff)


@bp.route("/employees/<int:user_id>/toggle", methods=["POST"])
@role_required("admin")
def toggle_employee(user_id):
    user = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    if user is None:
        flash("User not found.", "error")
    else:
        execute("UPDATE users SET is_active = ? WHERE id = ?", (0 if user["is_active"] else 1, user_id))
        flash(f"{user['name']} {'deactivated' if user['is_active'] else 'activated'}.", "success")
    return redirect(url_for("admin.employees"))


# ------------------------------------------------------------------ clients
@bp.route("/clients")
@role_required("admin")
def clients():
    rows = query_all(
        """SELECT u.*, COUNT(p.id) AS project_count
           FROM users u LEFT JOIN projects p ON p.client_id = u.id
           WHERE u.role='client' GROUP BY u.id ORDER BY u.created_at DESC"""
    )
    return render_template("admin/clients.html", clients=rows)


# ----------------------------------------------------------------- projects
@bp.route("/projects", methods=["GET", "POST"])
@role_required("admin")
def projects():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        client_id = request.form.get("client_id")
        team_lead_id = request.form.get("team_lead_id") or None
        category = request.form.get("category", "Video Editing")
        description = request.form.get("description", "").strip()
        budget = request.form.get("budget") or 0
        deadline = request.form.get("deadline") or None

        if not name or not client_id:
            flash("Project name and client are required.", "error")
        else:
            pid = execute(
                """INSERT INTO projects (name, category, client_id, team_lead_id,
                   description, budget, deadline) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (name, category, client_id, team_lead_id, description, budget, deadline),
            )
            if team_lead_id:
                notify(int(team_lead_id), f"You were assigned as lead on '{name}'.", url_for("team_lead.project_detail", project_id=pid))
            notify(int(client_id), f"Your project '{name}' has been created.", url_for("client.project_detail", project_id=pid))
            flash(f"Project '{name}' created.", "success")
        return redirect(url_for("admin.projects"))

    rows = query_all(
        """SELECT p.*, u.name AS client_name, t.name AS lead_name
           FROM projects p
           JOIN users u ON u.id = p.client_id
           LEFT JOIN users t ON t.id = p.team_lead_id
           ORDER BY p.created_at DESC"""
    )
    clients_list = query_all("SELECT id, name, company FROM users WHERE role='client' ORDER BY name")
    leads_list = query_all("SELECT id, name FROM users WHERE role='team_lead' ORDER BY name")
    return render_template(
        "admin/projects.html", projects=rows, clients=clients_list, leads=leads_list
    )


@bp.route("/projects/<int:project_id>")
@role_required("admin")
def project_detail(project_id):
    project = query_one(
        """SELECT p.*, u.name AS client_name, u.email AS client_email, t.name AS lead_name
           FROM projects p JOIN users u ON u.id = p.client_id
           LEFT JOIN users t ON t.id = p.team_lead_id WHERE p.id=?""",
        (project_id,),
    )
    if project is None:
        flash("Project not found.", "error")
        return redirect(url_for("admin.projects"))

    tasks = query_all(
        """SELECT t.*, u.name AS assignee_name FROM tasks t
           LEFT JOIN users u ON u.id = t.assigned_to
           WHERE t.project_id=? ORDER BY t.created_at""",
        (project_id,),
    )
    files = query_all(
        """SELECT f.*, u.name AS uploader_name FROM task_files f
           JOIN users u ON u.id = f.uploaded_by WHERE f.project_id=?
           ORDER BY f.uploaded_at DESC""",
        (project_id,),
    )
    messages = query_all(
        """SELECT m.*, u.name AS sender_name, u.role AS sender_role FROM messages m
           JOIN users u ON u.id = m.sender_id WHERE m.project_id=?
           ORDER BY m.created_at""",
        (project_id,),
    )
    invoices = query_all("SELECT * FROM invoices WHERE project_id=? ORDER BY issued_at DESC", (project_id,))
    leads_list = query_all("SELECT id, name FROM users WHERE role='team_lead' ORDER BY name")

    return render_template(
        "admin/project_detail.html", project=project, tasks=tasks, files=files,
        messages=messages, invoices=invoices, leads=leads_list,
        statuses=["Pending", "In Progress", "Review", "Revision", "Approved", "Delivered"],
    )


@bp.route("/projects/<int:project_id>/status", methods=["POST"])
@role_required("admin")
def update_project_status(project_id):
    status = request.form.get("status")
    project = query_one("SELECT * FROM projects WHERE id=?", (project_id,))
    if project and status:
        execute("UPDATE projects SET status=? WHERE id=?", (status, project_id))
        notify(project["client_id"], f"'{project['name']}' status changed to {status}.", url_for("client.project_detail", project_id=project_id))
        flash("Project status updated.", "success")
    return redirect(url_for("admin.project_detail", project_id=project_id))


@bp.route("/projects/<int:project_id>/assign-lead", methods=["POST"])
@role_required("admin")
def assign_lead(project_id):
    team_lead_id = request.form.get("team_lead_id") or None
    execute("UPDATE projects SET team_lead_id=? WHERE id=?", (team_lead_id, project_id))
    if team_lead_id:
        project = query_one("SELECT name FROM projects WHERE id=?", (project_id,))
        notify(int(team_lead_id), f"You were assigned as lead on '{project['name']}'.", url_for("team_lead.project_detail", project_id=project_id))
    flash("Team lead updated.", "success")
    return redirect(url_for("admin.project_detail", project_id=project_id))


@bp.route("/projects/<int:project_id>/invoice", methods=["POST"])
@role_required("admin")
def create_invoice(project_id):
    amount = request.form.get("amount")
    due_at = request.form.get("due_at") or None
    if not amount:
        flash("Enter an invoice amount.", "error")
    else:
        execute(
            "INSERT INTO invoices (project_id, amount, due_at) VALUES (?, ?, ?)",
            (project_id, amount, due_at),
        )
        project = query_one("SELECT client_id, name FROM projects WHERE id=?", (project_id,))
        notify(project["client_id"], f"A new invoice was issued for '{project['name']}'.", url_for("client.project_detail", project_id=project_id))
        flash("Invoice created.", "success")
    return redirect(url_for("admin.project_detail", project_id=project_id))


@bp.route("/invoices/<int:invoice_id>/mark-paid", methods=["POST"])
@role_required("admin")
def mark_invoice_paid(invoice_id):
    execute("UPDATE invoices SET status='Paid' WHERE id=?", (invoice_id,))
    flash("Invoice marked as paid.", "success")
    invoice = query_one("SELECT project_id FROM invoices WHERE id=?", (invoice_id,))
    return redirect(url_for("admin.project_detail", project_id=invoice["project_id"]))


@bp.route("/projects/<int:project_id>/message", methods=["POST"])
@role_required("admin")
def post_message(project_id):
    user = get_current_user()
    project = query_one("SELECT * FROM projects WHERE id=?", (project_id,))
    if project is None:
        flash("Project not found.", "error")
        return redirect(url_for("admin.projects"))

    body = request.form.get("body", "").strip()
    if body:
        execute("INSERT INTO messages (project_id, sender_id, body) VALUES (?, ?, ?)", (project_id, user["id"], body))
        notify(project["client_id"], f"New message on '{project['name']}'.", url_for("client.project_detail", project_id=project_id))
        if project["team_lead_id"]:
            notify(project["team_lead_id"], f"New message on '{project['name']}'.", url_for("team_lead.project_detail", project_id=project_id))
    return redirect(url_for("admin.project_detail", project_id=project_id))


# ------------------------------------------------------------------ finance
@bp.route("/finance")
@role_required("admin")
def finance():
    invoices = query_all(
        """SELECT i.*, p.name AS project_name, u.name AS client_name
           FROM invoices i JOIN projects p ON p.id = i.project_id
           JOIN users u ON u.id = p.client_id ORDER BY i.issued_at DESC"""
    )
    totals = {
        "paid": query_one("SELECT COALESCE(SUM(amount),0) s FROM invoices WHERE status='Paid'")["s"],
        "pending": query_one("SELECT COALESCE(SUM(amount),0) s FROM invoices WHERE status='Pending'")["s"],
        "overdue": query_one("SELECT COALESCE(SUM(amount),0) s FROM invoices WHERE status='Overdue'")["s"],
    }
    return render_template("admin/finance.html", invoices=invoices, totals=totals)

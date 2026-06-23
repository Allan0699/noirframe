import os
import uuid

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from werkzeug.utils import secure_filename

from db import query_all, query_one, execute
from decorators import role_required, get_current_user
from blueprints.helpers import notify, project_visible_to

bp = Blueprint("client", __name__, url_prefix="/client")


def _own_project_or_404(project_id, user):
    project = query_one("SELECT * FROM projects WHERE id=?", (project_id,))
    if project is None or not project_visible_to(user, project):
        abort(404)
    return project


@bp.route("/")
@role_required("client")
def dashboard():
    user = get_current_user()
    projects = query_all(
        """SELECT p.*, t.name AS lead_name FROM projects p
           LEFT JOIN users t ON t.id=p.team_lead_id
           WHERE p.client_id=? ORDER BY p.created_at DESC""",
        (user["id"],),
    )
    invoices_due = query_one(
        """SELECT COALESCE(SUM(i.amount),0) s FROM invoices i
           JOIN projects p ON p.id=i.project_id
           WHERE p.client_id=? AND i.status != 'Paid'""",
        (user["id"],),
    )["s"]
    return render_template("client/dashboard.html", projects=projects, invoices_due=invoices_due)


@bp.route("/projects/<int:project_id>")
@role_required("client")
def project_detail(project_id):
    user = get_current_user()
    project = _own_project_or_404(project_id, user)
    lead = query_one("SELECT name, email FROM users WHERE id=?", (project["team_lead_id"],)) if project["team_lead_id"] else None
    tasks = query_all(
        "SELECT title, status FROM tasks WHERE project_id=? ORDER BY created_at", (project_id,)
    )
    files = query_all(
        """SELECT f.*, u.name AS uploader_name FROM task_files f
           JOIN users u ON u.id=f.uploaded_by
           WHERE f.project_id=? AND f.kind='deliverable' ORDER BY f.uploaded_at DESC""",
        (project_id,),
    )
    references = query_all(
        """SELECT f.*, u.name AS uploader_name FROM task_files f
           JOIN users u ON u.id=f.uploaded_by
           WHERE f.project_id=? AND f.kind='reference' ORDER BY f.uploaded_at DESC""",
        (project_id,),
    )
    messages = query_all(
        """SELECT m.*, u.name AS sender_name, u.role AS sender_role FROM messages m
           JOIN users u ON u.id=m.sender_id WHERE m.project_id=? ORDER BY m.created_at""",
        (project_id,),
    )
    invoices = query_all("SELECT * FROM invoices WHERE project_id=? ORDER BY issued_at DESC", (project_id,))
    return render_template(
        "client/project_detail.html", project=project, lead=lead, tasks=tasks,
        files=files, references=references, messages=messages, invoices=invoices,
        statuses=["Pending", "In Progress", "Review", "Revision", "Approved", "Delivered"],
    )


@bp.route("/projects/<int:project_id>/request-revision", methods=["POST"])
@role_required("client")
def request_revision(project_id):
    user = get_current_user()
    project = _own_project_or_404(project_id, user)
    note = request.form.get("note", "").strip()

    execute("UPDATE projects SET status='Revision' WHERE id=?", (project_id,))
    execute(
        "INSERT INTO messages (project_id, sender_id, body) VALUES (?, ?, ?)",
        (project_id, user["id"], f"Revision requested: {note}" if note else "Revision requested."),
    )
    if project["team_lead_id"]:
        notify(project["team_lead_id"], f"Client requested a revision on '{project['name']}'.", url_for("team_lead.project_detail", project_id=project_id))
    else:
        admins = query_all("SELECT id FROM users WHERE role='admin'")
        for a in admins:
            notify(a["id"], f"Client requested a revision on '{project['name']}'.", url_for("admin.project_detail", project_id=project_id))
    flash("Revision request sent.", "success")
    return redirect(url_for("client.project_detail", project_id=project_id))


@bp.route("/projects/<int:project_id>/upload-reference", methods=["POST"])
@role_required("client")
def upload_reference(project_id):
    user = get_current_user()
    project = _own_project_or_404(project_id, user)

    file = request.files.get("file")
    if not file or file.filename == "":
        flash("Choose a file to upload.", "error")
        return redirect(url_for("client.project_detail", project_id=project_id))

    project_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], f"project_{project_id}")
    os.makedirs(project_dir, exist_ok=True)
    original_name = secure_filename(file.filename)
    stored_name = f"{uuid.uuid4().hex}_{original_name}"
    file.save(os.path.join(project_dir, stored_name))

    execute(
        """INSERT INTO task_files (project_id, uploaded_by, original_name, stored_name, kind)
           VALUES (?, ?, ?, ?, 'reference')""",
        (project_id, user["id"], original_name, stored_name),
    )
    if project["team_lead_id"]:
        notify(project["team_lead_id"], f"Client uploaded a reference file to '{project['name']}'.", url_for("team_lead.project_detail", project_id=project_id))
    flash("Reference uploaded.", "success")
    return redirect(url_for("client.project_detail", project_id=project_id))


@bp.route("/projects/<int:project_id>/message", methods=["POST"])
@role_required("client")
def post_message(project_id):
    user = get_current_user()
    project = _own_project_or_404(project_id, user)
    body = request.form.get("body", "").strip()
    if body:
        execute("INSERT INTO messages (project_id, sender_id, body) VALUES (?, ?, ?)", (project_id, user["id"], body))
        if project["team_lead_id"]:
            notify(project["team_lead_id"], f"New client message on '{project['name']}'.", url_for("team_lead.project_detail", project_id=project_id))
    return redirect(url_for("client.project_detail", project_id=project_id))


@bp.route("/invoices")
@role_required("client")
def invoices():
    user = get_current_user()
    rows = query_all(
        """SELECT i.*, p.name AS project_name FROM invoices i
           JOIN projects p ON p.id=i.project_id WHERE p.client_id=?
           ORDER BY i.issued_at DESC""",
        (user["id"],),
    )
    return render_template("client/invoices.html", invoices=rows)


@bp.route("/invoices/<int:invoice_id>/pay", methods=["POST"])
@role_required("client")
def pay_invoice(invoice_id):
    """Demo-only payment simulation -- no real payment gateway is wired up."""
    user = get_current_user()
    invoice = query_one(
        """SELECT i.*, p.client_id FROM invoices i JOIN projects p ON p.id=i.project_id
           WHERE i.id=?""",
        (invoice_id,),
    )
    if invoice is None or invoice["client_id"] != user["id"]:
        abort(404)
    execute("UPDATE invoices SET status='Paid' WHERE id=?", (invoice_id,))
    flash("Payment recorded (demo only -- no real payment gateway is connected).", "success")
    return redirect(url_for("client.invoices"))

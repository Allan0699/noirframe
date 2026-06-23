from flask import Blueprint, render_template, request, redirect, url_for, flash, abort

from db import query_all, query_one, execute
from decorators import role_required, get_current_user
from blueprints.helpers import notify, recalc_project_progress, project_visible_to

bp = Blueprint("team_lead", __name__, url_prefix="/team-lead")


def _own_project_or_404(project_id, user):
    project = query_one("SELECT * FROM projects WHERE id=?", (project_id,))
    if project is None or not project_visible_to(user, project):
        abort(404)
    return project


@bp.route("/")
@role_required("team_lead")
def dashboard():
    user = get_current_user()
    projects = query_all(
        """SELECT p.*, u.name AS client_name FROM projects p
           JOIN users u ON u.id=p.client_id WHERE p.team_lead_id=?
           ORDER BY p.created_at DESC""",
        (user["id"],),
    )
    open_tasks = query_all(
        """SELECT t.*, p.name AS project_name FROM tasks t
           JOIN projects p ON p.id=t.project_id
           WHERE p.team_lead_id=? AND t.status='Under Review'
           ORDER BY t.updated_at""",
        (user["id"],),
    )
    stats = {
        "active_projects": sum(1 for p in projects if p["status"] != "Delivered"),
        "awaiting_review": len(open_tasks),
        "team_size": query_one("SELECT COUNT(*) c FROM users WHERE role='employee' AND is_active=1")["c"],
    }
    return render_template("team_lead/dashboard.html", projects=projects, open_tasks=open_tasks, stats=stats)


@bp.route("/projects")
@role_required("team_lead")
def projects():
    user = get_current_user()
    rows = query_all(
        """SELECT p.*, u.name AS client_name FROM projects p
           JOIN users u ON u.id=p.client_id WHERE p.team_lead_id=?
           ORDER BY p.created_at DESC""",
        (user["id"],),
    )
    return render_template("team_lead/projects.html", projects=rows)


@bp.route("/employees")
@role_required("team_lead")
def employees():
    rows = query_all(
        """SELECT u.*,
             SUM(CASE WHEN t.status NOT IN ('Completed') THEN 1 ELSE 0 END) AS open_tasks,
             SUM(CASE WHEN t.status='Completed' THEN 1 ELSE 0 END) AS done_tasks
           FROM users u LEFT JOIN tasks t ON t.assigned_to = u.id
           WHERE u.role='employee' GROUP BY u.id ORDER BY u.name"""
    )
    return render_template("team_lead/employees.html", employees=rows)


@bp.route("/projects/<int:project_id>")
@role_required("team_lead")
def project_detail(project_id):
    user = get_current_user()
    project = _own_project_or_404(project_id, user)
    client = query_one("SELECT name, email, company FROM users WHERE id=?", (project["client_id"],))
    tasks = query_all(
        """SELECT t.*, u.name AS assignee_name FROM tasks t
           LEFT JOIN users u ON u.id=t.assigned_to
           WHERE t.project_id=? ORDER BY t.created_at""",
        (project_id,),
    )
    employees_list = query_all("SELECT id, name FROM users WHERE role='employee' AND is_active=1 ORDER BY name")
    files = query_all(
        """SELECT f.*, u.name AS uploader_name FROM task_files f
           JOIN users u ON u.id=f.uploaded_by WHERE f.project_id=? ORDER BY f.uploaded_at DESC""",
        (project_id,),
    )
    messages = query_all(
        """SELECT m.*, u.name AS sender_name, u.role AS sender_role FROM messages m
           JOIN users u ON u.id=m.sender_id WHERE m.project_id=? ORDER BY m.created_at""",
        (project_id,),
    )
    return render_template(
        "team_lead/project_detail.html", project=project, client=client, tasks=tasks,
        employees=employees_list, files=files, messages=messages,
    )


@bp.route("/projects/<int:project_id>/tasks", methods=["POST"])
@role_required("team_lead")
def create_task(project_id):
    user = get_current_user()
    project = _own_project_or_404(project_id, user)

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    assigned_to = request.form.get("assigned_to") or None
    priority = request.form.get("priority", "Medium")
    due_date = request.form.get("due_date") or None

    if not title:
        flash("Task title is required.", "error")
    else:
        status = "Assigned" if assigned_to else "Not Started"
        task_id = execute(
            """INSERT INTO tasks (project_id, title, description, assigned_to,
               priority, status, due_date) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (project_id, title, description, assigned_to, priority, status, due_date),
        )
        if assigned_to:
            notify(int(assigned_to), f"New task assigned: '{title}' ({project['name']}).", url_for("employee.task_detail", task_id=task_id))
        recalc_project_progress(project_id)
        flash("Task created.", "success")
    return redirect(url_for("team_lead.project_detail", project_id=project_id))


@bp.route("/tasks/<int:task_id>/review", methods=["POST"])
@role_required("team_lead")
def review_task(task_id):
    user = get_current_user()
    task = query_one("SELECT * FROM tasks WHERE id=?", (task_id,))
    if task is None:
        abort(404)
    project = _own_project_or_404(task["project_id"], user)

    decision = request.form.get("decision")  # 'approve' or 'revise'
    if decision == "approve":
        execute("UPDATE tasks SET status='Completed', updated_at=datetime('now') WHERE id=?", (task_id,))
        flash(f"'{task['title']}' approved.", "success")
    elif decision == "revise":
        note = request.form.get("note", "").strip()
        execute("UPDATE tasks SET status='Revision Required', updated_at=datetime('now') WHERE id=?", (task_id,))
        if task["assigned_to"]:
            body = f"Revision requested on '{task['title']}'"
            if note:
                body += f": {note}"
            notify(task["assigned_to"], body, url_for("employee.task_detail", task_id=task_id))
        flash("Revision requested.", "success")
    recalc_project_progress(project["id"])
    return redirect(url_for("team_lead.project_detail", project_id=project["id"]))


@bp.route("/projects/<int:project_id>/message", methods=["POST"])
@role_required("team_lead")
def post_message(project_id):
    user = get_current_user()
    project = _own_project_or_404(project_id, user)
    body = request.form.get("body", "").strip()
    if body:
        execute("INSERT INTO messages (project_id, sender_id, body) VALUES (?, ?, ?)", (project_id, user["id"], body))
        notify(project["client_id"], f"New message on '{project['name']}'.", url_for("client.project_detail", project_id=project_id))
    return redirect(url_for("team_lead.project_detail", project_id=project_id))

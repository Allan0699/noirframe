import os
import uuid

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from werkzeug.utils import secure_filename

from db import query_all, query_one, execute
from decorators import role_required, get_current_user
from blueprints.helpers import notify, recalc_project_progress

bp = Blueprint("employee", __name__, url_prefix="/employee")

TASK_STATUSES = ["Not Started", "Assigned", "Working", "Under Review", "Revision Required", "Completed"]


@bp.route("/")
@role_required("employee")
def dashboard():
    user = get_current_user()
    tasks = query_all(
        """SELECT t.*, p.name AS project_name FROM tasks t
           JOIN projects p ON p.id=t.project_id WHERE t.assigned_to=?
           ORDER BY CASE t.priority WHEN 'Urgent' THEN 0 WHEN 'High' THEN 1
                WHEN 'Medium' THEN 2 ELSE 3 END, t.due_date""",
        (user["id"],),
    )
    stats = {
        "open": sum(1 for t in tasks if t["status"] not in ("Completed",)),
        "due_soon": sum(1 for t in tasks if t["status"] not in ("Completed",) and t["due_date"]),
        "completed": sum(1 for t in tasks if t["status"] == "Completed"),
    }
    open_clock = query_one(
        "SELECT * FROM time_logs WHERE employee_id=? AND clock_out IS NULL ORDER BY clock_in DESC LIMIT 1",
        (user["id"],),
    )
    notifications = query_all(
        "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 8",
        (user["id"],),
    )
    return render_template(
        "employee/dashboard.html", tasks=tasks, stats=stats, open_clock=open_clock,
        notifications=notifications,
    )


@bp.route("/tasks")
@role_required("employee")
def tasks():
    user = get_current_user()
    rows = query_all(
        """SELECT t.*, p.name AS project_name FROM tasks t
           JOIN projects p ON p.id=t.project_id WHERE t.assigned_to=?
           ORDER BY t.created_at DESC""",
        (user["id"],),
    )
    return render_template("employee/tasks.html", tasks=rows)


@bp.route("/tasks/<int:task_id>")
@role_required("employee")
def task_detail(task_id):
    user = get_current_user()
    task = query_one(
        """SELECT t.*, p.name AS project_name, p.id AS project_id, p.description AS project_description
           FROM tasks t JOIN projects p ON p.id=t.project_id WHERE t.id=?""",
        (task_id,),
    )
    if task is None or task["assigned_to"] != user["id"]:
        abort(404)
    files = query_all(
        "SELECT * FROM task_files WHERE task_id=? ORDER BY uploaded_at DESC", (task_id,)
    )
    return render_template(
        "employee/task_detail.html", task=task, files=files, statuses=TASK_STATUSES
    )


@bp.route("/tasks/<int:task_id>/status", methods=["POST"])
@role_required("employee")
def update_task_status(task_id):
    user = get_current_user()
    task = query_one("SELECT * FROM tasks WHERE id=?", (task_id,))
    if task is None or task["assigned_to"] != user["id"]:
        abort(404)

    new_status = request.form.get("status")
    if new_status not in TASK_STATUSES:
        flash("Invalid status.", "error")
        return redirect(url_for("employee.task_detail", task_id=task_id))

    execute("UPDATE tasks SET status=?, updated_at=datetime('now') WHERE id=?", (new_status, task_id))

    if new_status == "Under Review":
        project = query_one("SELECT team_lead_id, name FROM projects WHERE id=?", (task["project_id"],))
        if project and project["team_lead_id"]:
            notify(project["team_lead_id"], f"'{task['title']}' submitted for review.", url_for("team_lead.project_detail", project_id=task["project_id"]))

    recalc_project_progress(task["project_id"])
    flash("Task status updated.", "success")
    return redirect(url_for("employee.task_detail", task_id=task_id))


@bp.route("/tasks/<int:task_id>/upload", methods=["POST"])
@role_required("employee")
def upload_file(task_id):
    user = get_current_user()
    task = query_one("SELECT * FROM tasks WHERE id=?", (task_id,))
    if task is None or task["assigned_to"] != user["id"]:
        abort(404)

    file = request.files.get("file")
    if not file or file.filename == "":
        flash("Choose a file to upload.", "error")
        return redirect(url_for("employee.task_detail", task_id=task_id))

    project_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], f"project_{task['project_id']}")
    os.makedirs(project_dir, exist_ok=True)

    original_name = secure_filename(file.filename)
    stored_name = f"{uuid.uuid4().hex}_{original_name}"
    file.save(os.path.join(project_dir, stored_name))

    execute(
        """INSERT INTO task_files (project_id, task_id, uploaded_by, original_name,
           stored_name, kind) VALUES (?, ?, ?, ?, ?, 'deliverable')""",
        (task["project_id"], task_id, user["id"], original_name, stored_name),
    )
    flash("File uploaded.", "success")
    return redirect(url_for("employee.task_detail", task_id=task_id))


# --------------------------------------------------------------- time clock
@bp.route("/clock-in", methods=["POST"])
@role_required("employee")
def clock_in():
    user = get_current_user()
    existing = query_one(
        "SELECT id FROM time_logs WHERE employee_id=? AND clock_out IS NULL", (user["id"],)
    )
    if existing is None:
        execute("INSERT INTO time_logs (employee_id) VALUES (?)", (user["id"],))
        flash("Clocked in.", "success")
    return redirect(url_for("employee.dashboard"))


@bp.route("/clock-out", methods=["POST"])
@role_required("employee")
def clock_out():
    user = get_current_user()
    execute(
        """UPDATE time_logs SET clock_out=datetime('now')
           WHERE employee_id=? AND clock_out IS NULL""",
        (user["id"],),
    )
    flash("Clocked out.", "success")
    return redirect(url_for("employee.dashboard"))


@bp.route("/timesheet")
@role_required("employee")
def timesheet():
    import datetime as dt

    user = get_current_user()
    rows = query_all(
        "SELECT * FROM time_logs WHERE employee_id=? ORDER BY clock_in DESC LIMIT 50",
        (user["id"],),
    )
    logs = []
    for r in rows:
        entry = dict(r)
        if r["clock_out"]:
            start = dt.datetime.strptime(r["clock_in"], "%Y-%m-%d %H:%M:%S")
            end = dt.datetime.strptime(r["clock_out"], "%Y-%m-%d %H:%M:%S")
            minutes = int((end - start).total_seconds() // 60)
            entry["duration"] = f"{minutes // 60}h {minutes % 60}m"
        else:
            entry["duration"] = "In progress"
        logs.append(entry)
    return render_template("employee/timesheet.html", logs=logs)

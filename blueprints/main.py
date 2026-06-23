import os

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    send_from_directory, abort, current_app, jsonify,
)

from db import query_all, query_one, execute
from decorators import login_required, get_current_user
from blueprints.helpers import project_visible_to

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    portfolio_items = query_all("SELECT * FROM portfolio_items ORDER BY created_at DESC")
    testimonials = query_all("SELECT * FROM testimonials")
    return render_template(
        "main/index.html",
        portfolio_items=portfolio_items,
        testimonials=testimonials,
    )


@bp.route("/contact", methods=["POST"])
def contact():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()

    if not name or "@" not in email or len(message) < 5:
        flash("Please fill in your name, a valid email, and a short message.", "error")
        return redirect(url_for("main.index", _anchor="contact"))

    execute(
        "INSERT INTO contact_messages (name, email, message) VALUES (?, ?, ?)",
        (name, email, message),
    )
    flash("Thanks -- your message has been sent. We'll be in touch within one business day.", "success")
    return redirect(url_for("main.index", _anchor="contact"))


@bp.route("/files/<int:file_id>/download")
@login_required
def download_file(file_id):
    user = get_current_user()
    record = query_one("SELECT * FROM task_files WHERE id=?", (file_id,))
    if record is None:
        abort(404)
    project = query_one("SELECT * FROM projects WHERE id=?", (record["project_id"],))
    if project is None or not project_visible_to(user, project):
        abort(404)

    directory = os.path.join(current_app.config["UPLOAD_FOLDER"], f"project_{record['project_id']}")
    return send_from_directory(directory, record["stored_name"], as_attachment=True, download_name=record["original_name"])


@bp.route("/api/notifications")
@login_required
def notifications():
    user = get_current_user()
    rows = query_all(
        "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 15",
        (user["id"],),
    )
    unread = query_one(
        "SELECT COUNT(*) c FROM notifications WHERE user_id=? AND is_read=0", (user["id"],)
    )["c"]
    return jsonify({
        "unread": unread,
        "items": [dict(r) for r in rows],
    })


@bp.route("/api/notifications/read-all", methods=["POST"])
@login_required
def mark_notifications_read():
    user = get_current_user()
    execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (user["id"],))
    return jsonify({"ok": True})

from db import query_one, query_all, execute


def notify(user_id, body, link=None):
    if user_id is None:
        return
    execute(
        "INSERT INTO notifications (user_id, body, link) VALUES (?, ?, ?)",
        (user_id, body, link),
    )


def recalc_project_progress(project_id):
    """Project progress = % of tasks marked Completed. Also nudges the
    project status forward when every task is done."""
    tasks = query_all("SELECT status FROM tasks WHERE project_id = ?", (project_id,))
    if not tasks:
        progress = 0
    else:
        done = sum(1 for t in tasks if t["status"] == "Completed")
        progress = round((done / len(tasks)) * 100)

    execute("UPDATE projects SET progress = ? WHERE id = ?", (progress, project_id))

    if progress == 100:
        project = query_one("SELECT status FROM projects WHERE id = ?", (project_id,))
        if project and project["status"] not in ("Approved", "Delivered"):
            execute(
                "UPDATE projects SET status = 'Review' WHERE id = ?", (project_id,)
            )
    return progress


def project_visible_to(user, project):
    """Authorization check: can this user view/act on this project?"""
    if user["role"] == "admin":
        return True
    if user["role"] == "team_lead":
        return project["team_lead_id"] == user["id"]
    if user["role"] == "client":
        return project["client_id"] == user["id"]
    if user["role"] == "employee":
        task = query_one(
            "SELECT id FROM tasks WHERE project_id = ? AND assigned_to = ? LIMIT 1",
            (project["id"], user["id"]),
        )
        return task is not None
    return False

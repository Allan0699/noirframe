"""
Auth helpers: who is logged in, and route decorators that enforce it.

Authentication itself is plain Flask sessions (a signed cookie holding the
user id). No third-party auth library is required. Passwords are hashed
with Werkzeug's security helpers (already a Flask dependency).
"""

from functools import wraps

from flask import session, redirect, url_for, flash, g, request

from db import query_one

ROLE_HOME = {
    "admin": "admin.dashboard",
    "team_lead": "team_lead.dashboard",
    "employee": "employee.dashboard",
    "client": "client.dashboard",
}


def get_current_user():
    if "user" not in g:
        user_id = session.get("user_id")
        g.user = query_one("SELECT * FROM users WHERE id = ?", (user_id,)) if user_id else None
    return g.user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if get_current_user() is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = get_current_user()
            if user is None:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth.login", next=request.path))
            if user["role"] not in roles:
                flash("You don't have access to that area.", "error")
                return redirect(url_for(ROLE_HOME.get(user["role"], "main.index")))
            return view(*args, **kwargs)

        return wrapped

    return decorator

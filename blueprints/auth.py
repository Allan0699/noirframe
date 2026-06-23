from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import check_password_hash, generate_password_hash

from db import query_one, execute
from decorators import get_current_user, ROLE_HOME

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if get_current_user() is not None:
        return redirect(url_for(ROLE_HOME[g.user["role"]]))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = query_one("SELECT * FROM users WHERE email = ?", (email,))
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Incorrect email or password.", "error")
            return render_template("auth/login.html", email=email)

        if not user["is_active"]:
            flash("This account has been deactivated. Contact your administrator.", "error")
            return render_template("auth/login.html", email=email)

        session.clear()
        session["user_id"] = user["id"]
        flash(f"Welcome back, {user['name'].split(' ')[0]}.", "success")

        next_url = request.args.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        return redirect(url_for(ROLE_HOME[user["role"]]))

    return render_template("auth/login.html", email="")


@bp.route("/register", methods=["GET", "POST"])
def register():
    """Self-service signup -- always creates a client account.
    Internal accounts (admin / team lead / employee) are created by an
    administrator from the admin panel instead."""
    if get_current_user() is not None:
        return redirect(url_for(ROLE_HOME[g.user["role"]]))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        company = request.form.get("company", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        errors = []
        if len(name) < 2:
            errors.append("Please enter your full name.")
        if "@" not in email:
            errors.append("Please enter a valid email address.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if query_one("SELECT id FROM users WHERE email = ?", (email,)):
            errors.append("An account with that email already exists.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "auth/register.html", name=name, company=company, email=email
            )

        user_id = execute(
            "INSERT INTO users (name, email, password_hash, role, company) "
            "VALUES (?, ?, ?, 'client', ?)",
            (name, email, generate_password_hash(password), company),
        )
        session.clear()
        session["user_id"] = user_id
        flash("Account created. Welcome to NOIRFRAME.", "success")
        return redirect(url_for("client.dashboard"))

    return render_template("auth/register.html", name="", company="", email="")


@bp.route("/logout")
def logout():
    session.clear()
    flash("You've been logged out.", "success")
    return redirect(url_for("main.index"))

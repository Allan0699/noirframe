"""
Seeds demo data the first time the app boots against an empty database, so
the platform is immediately explorable from every role without manual setup.

Demo logins (also printed to the console on first boot):
  Admin       admin@noirframe.studio      / admin12345
  Team Lead   priya@noirframe.studio      / lead12345
  Employee    diego@noirframe.studio      / employee12345
  Employee    mei@noirframe.studio        / employee12345
  Client      client@brightpeak.com       / client12345
"""

from werkzeug.security import generate_password_hash

from db import query_one, execute


def seed_if_empty(app):
    with app.app_context():
        if query_one("SELECT id FROM users LIMIT 1") is not None:
            return  # already seeded

        pw = lambda raw: generate_password_hash(raw)

        admin_id = execute(
            "INSERT INTO users (name, email, password_hash, role, title) VALUES (?,?,?,?,?)",
            ("Alex Moreau", "admin@noirframe.studio", pw("admin12345"), "admin", "Studio Director"),
        )
        lead_id = execute(
            "INSERT INTO users (name, email, password_hash, role, title) VALUES (?,?,?,?,?)",
            ("Priya Nair", "priya@noirframe.studio", pw("lead12345"), "team_lead", "Senior Team Lead"),
        )
        emp1_id = execute(
            "INSERT INTO users (name, email, password_hash, role, title) VALUES (?,?,?,?,?)",
            ("Diego Ramirez", "diego@noirframe.studio", pw("employee12345"), "employee", "Motion Designer"),
        )
        emp2_id = execute(
            "INSERT INTO users (name, email, password_hash, role, title) VALUES (?,?,?,?,?)",
            ("Mei Chen", "mei@noirframe.studio", pw("employee12345"), "employee", "Video Editor"),
        )
        client1_id = execute(
            "INSERT INTO users (name, email, password_hash, role, company) VALUES (?,?,?,?,?)",
            ("Jordan Blake", "client@brightpeak.com", pw("client12345"), "client", "BrightPeak Outdoor Co."),
        )
        client2_id = execute(
            "INSERT INTO users (name, email, password_hash, role, company) VALUES (?,?,?,?,?)",
            ("Sara Whitfield", "sara@lumenfit.com", pw("client12345"), "client", "LumenFit Studios"),
        )

        # ---- projects -------------------------------------------------
        p1 = execute(
            """INSERT INTO projects (name, category, client_id, team_lead_id, description,
               budget, deadline, status, progress) VALUES (?,?,?,?,?,?,?,?,?)""",
            ("BrightPeak Summer Launch Film", "Brand Commercials", client1_id, lead_id,
             "90-second hero film for the summer product launch, plus 3 social cutdowns.",
             8500, "2026-07-15", "In Progress", 40),
        )
        p2 = execute(
            """INSERT INTO projects (name, category, client_id, team_lead_id, description,
               budget, deadline, status, progress) VALUES (?,?,?,?,?,?,?,?,?)""",
            ("LumenFit App Onboarding Animation", "2D Animation", client2_id, lead_id,
             "60-second explainer animation for the LumenFit app onboarding flow.",
             4200, "2026-08-01", "Review", 80),
        )
        p3 = execute(
            """INSERT INTO projects (name, category, client_id, budget, deadline, status, progress)
               VALUES (?,?,?,?,?,?,?)""",
            ("BrightPeak Q3 Social Pack", "Social Media Content", client1_id,
             2100, "2026-09-10", "Pending", 0),
        )

        # ---- tasks ------------------------------------------------------
        execute(
            "INSERT INTO tasks (project_id, title, description, assigned_to, priority, status, due_date) VALUES (?,?,?,?,?,?,?)",
            (p1, "Rough cut assembly", "Assemble selects into a rough 90s cut.", emp2_id, "High", "Completed", "2026-06-20"),
        )
        execute(
            "INSERT INTO tasks (project_id, title, description, assigned_to, priority, status, due_date) VALUES (?,?,?,?,?,?,?)",
            (p1, "Color grade pass", "Apply the agreed warm-summer LUT and grade.", emp2_id, "Medium", "Working", "2026-06-28"),
        )
        execute(
            "INSERT INTO tasks (project_id, title, description, assigned_to, priority, status, due_date) VALUES (?,?,?,?,?,?,?)",
            (p1, "Motion graphics titles", "Animate opening logo reveal and lower thirds.", emp1_id, "Medium", "Not Started", "2026-07-02"),
        )
        execute(
            "INSERT INTO tasks (project_id, title, description, assigned_to, priority, status, due_date) VALUES (?,?,?,?,?,?,?)",
            (p2, "Character rig setup", "Rig the two onboarding mascot characters.", emp1_id, "High", "Completed", "2026-06-10"),
        )
        execute(
            "INSERT INTO tasks (project_id, title, description, assigned_to, priority, status, due_date) VALUES (?,?,?,?,?,?,?)",
            (p2, "Scene 3-5 animation", "Animate the workout-tracking sequence.", emp1_id, "High", "Under Review", "2026-06-22"),
        )

        execute("UPDATE projects SET ai_summary=NULL")

        # ---- portfolio + testimonials ------------------------------------
        portfolio = [
            ("Aurora Skincare -- Launch Film", "Brand Commercials", "A 60-second hero film built around a single unbroken macro shot."),
            ("Kestrel Bikes -- Trail Edit", "Video Editing", "Fast-cut adventure edit for a product line relaunch."),
            ("Origin Coffee -- Brand World", "2D Animation", "A flat-illustration explainer establishing a new visual identity."),
            ("Northwind Games -- Cinematic Trailer", "3D Animation / CGI", "Full CGI cinematic trailer with custom character rigs."),
            ("Verve Fitness -- Social Series", "Social Media Content", "A 12-part short-form series optimized for retention."),
            ("Hallow & Pine -- Wedding Film", "Wedding Films", "A documentary-style same-day edit delivered before the reception ended."),
        ]
        for title, category, desc in portfolio:
            execute(
                "INSERT INTO portfolio_items (title, category, description) VALUES (?,?,?)",
                (title, category, desc),
            )

        testimonials = [
            ("Jordan Blake", "Marketing Director, BrightPeak Outdoor", "NOIRFRAME turned a vague brief into a launch film that outperformed every benchmark we had. The client portal made revisions painless."),
            ("Sara Whitfield", "Founder, LumenFit", "Communication was the difference. We always knew exactly where our animation stood, down to the task."),
            ("Marcus Yi", "Brand Lead, Kestrel Bikes", "Fast, sharp, and genuinely collaborative -- our trail edit shipped two days early."),
        ]
        for name, role, quote in testimonials:
            execute(
                "INSERT INTO testimonials (client_name, role_company, quote) VALUES (?,?,?)",
                (name, role, quote),
            )

        print("\n" + "=" * 60)
        print(" NOIRFRAME demo data seeded. Sign in with:")
        print(" Admin     admin@noirframe.studio     / admin12345")
        print(" Team Lead priya@noirframe.studio     / lead12345")
        print(" Employee  diego@noirframe.studio     / employee12345")
        print(" Employee  mei@noirframe.studio       / employee12345")
        print(" Client    client@brightpeak.com      / client12345")
        print("=" * 60 + "\n")

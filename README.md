# NOIRFRAME -- Animation & Video Editing Agency Platform

A working Flask starter platform for a video/animation agency: a public
marketing site plus four role-based portals (Admin, Team Lead, Employee,
Client), project & task management, file uploads, messaging, notifications,
invoicing, and three Gemini-powered AI features.

This is a **solid, runnable foundation** -- not a finished enterprise SaaS.
See "What this is (and isn't)" near the bottom before you show it to a client
or put real data in it.

---

## 1. Setup (5 minutes)

**Requirements:** Python 3.10+ and a free [Gemini API key](https://aistudio.google.com/app/apikey)
(the AI features will show a friendly error if you skip this -- everything
else still works without one).

```bash
# 1. Unzip, then open the folder in VS Code (File > Open Folder...)
cd noirframe-platform

# 2. Create a virtual environment
python -m venv venv

# 3. Activate it
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows (cmd or PowerShell)

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create your .env file
cp .env.example .env            # macOS / Linux
copy .env.example .env          # Windows
# then open .env and paste your GEMINI_API_KEY

# 6. Run it
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

The database (SQLite) and demo data are created automatically on first run.
The console will print demo login credentials -- they're also listed below
and on the sign-in page itself.

### Demo logins

| Role | Email | Password |
|---|---|---|
| Admin | admin@noirframe.studio | admin12345 |
| Team Lead | priya@noirframe.studio | lead12345 |
| Employee | diego@noirframe.studio | employee12345 |
| Employee | mei@noirframe.studio | employee12345 |
| Client | client@brightpeak.com | client12345 |

New clients can also self-register from the "Start Your Project" button on
the landing page.

**Change these before deploying anywhere public** -- either edit
`seed_data.py` before the first run, or change passwords from the database
directly (there's no in-app "change password" flow yet -- see the roadmap
below).

---

## 2. What's included

- **Public site**: hero, services, pricing (monthly/per-project toggle),
  filterable portfolio, testimonials, contact form, and an AI support
  chatbot ("Ask Aria") powered by Gemini.
- **Admin panel**: studio-wide stats, employee/team-lead management,
  client list, project creation & oversight, status pipeline control,
  invoicing, and a finance dashboard.
- **Team Lead panel**: projects they lead, task creation & assignment,
  reviewing/approving submitted work or requesting revisions, an
  employee roster, and per-project messaging.
- **Employee panel**: assigned tasks sorted by priority, status updates,
  deliverable file uploads, and a simple time clock with a timesheet view.
- **Client portal**: project status pipeline & progress, deliverable
  downloads, reference uploads, revision requests, project messaging,
  and invoice payment (simulated -- see below).
- **AI features (Gemini)**:
  1. **Cost & timeline estimator** (Admin/Team Lead) -- draft a ballpark
     quote from a scope description.
  2. **Project summary generator** (Admin/Team Lead) -- turns a project's
     tasks into a client-ready status update.
  3. **Support chatbot** (public) -- answers visitor questions about
     services and pricing.
- **Notifications**: an in-app bell with unread counts, triggered by task
  assignment, status changes, revision requests, and new messages.
- Role-based auth, password hashing, and per-project access control (a
  client can only ever see their own projects; an employee only sees tasks
  assigned to them; etc.).

## 3. Project structure

```
noirframe-platform/
├── app.py                  # Flask app factory & entry point
├── config.py                # Config loaded from .env
├── db.py                    # SQLite connection helpers (no ORM)
├── decorators.py            # @login_required / @role_required
├── gemini_client.py         # Thin wrapper around the Gemini REST API
├── seed_data.py              # Demo data, runs once on an empty database
├── database/
│   └── schema.sql           # Table definitions
├── blueprints/
│   ├── main.py               # Landing page, contact form, downloads, notifications API
│   ├── auth.py                # Login / client registration / logout
│   ├── admin.py               # Admin panel routes
│   ├── team_lead.py           # Team lead panel routes
│   ├── employee.py            # Employee panel routes
│   ├── client.py               # Client portal routes
│   ├── ai.py                   # Gemini-powered endpoints
│   └── helpers.py              # Shared notification / progress / auth-check helpers
├── templates/                # Jinja2 templates (one folder per portal)
└── static/
    ├── css/style.css          # The whole design system
    ├── js/                    # main.js (landing) + dashboard.js (portals)
    └── uploads/                # Uploaded files land here, per project
```

No ORM, no frontend build step, no JS framework -- just Flask, Jinja, vanilla
JS, and SQLite. That keeps `pip install` fast and the codebase easy to read
end to end.

## 4. Adding more demo data / resetting

To reset everything, stop the server and delete `database/noirframe.db`,
then restart -- it will reseed automatically. Uploaded files in
`static/uploads/` aren't auto-cleaned, so delete that folder's contents too
if you want a totally clean slate.

---

## 5. What this is (and isn't)

The original brief asked for an enterprise-grade platform with real-time
chat, payroll, contracts/e-signatures, audit logs, thousands-of-users
scalability, and more. Building all of that correctly is realistically a
multi-month effort for a team, not a single generated codebase. This starter
gives you a correctly structured foundation for the **core** of that vision
(auth, roles, projects, tasks, files, messaging, invoicing, AI) that you can
extend piece by piece. Specifically **not** included yet, by design:

- **Real-time chat.** Messages use a normal page reload, not WebSockets.
- **Real payments.** The "Pay now" button just flips an invoice to "Paid" --
  there's no Stripe/PayPal integration.
- **Email/SMS notifications.** Notifications are in-app only.
- **Contracts, e-signatures, calendar/meeting scheduling.**
- **Granular permissions** beyond the four fixed roles.
- **Production hardening**: rate limiting, CSRF tokens on forms, audit
  logs, automated backups, horizontal scaling, cloud file storage.
- **Password reset / 2FA** -- there's a `change password` table column for
  it, but no flow yet.

If you want help adding any of these next, the codebase is organized so each
one is a contained addition (a new blueprint, a couple of template files,
and a schema migration) rather than a rewrite.

## 6. Troubleshooting

- **"GEMINI_API_KEY" errors in the AI panels**: add a key to `.env` and
  restart the server. Everything else in the app works without one.
- **Port already in use**: run `PORT=5050 python app.py` and visit
  `http://127.0.0.1:5050` instead.
- **Changes to `database/schema.sql` not showing up**: the schema only runs
  `CREATE TABLE IF NOT EXISTS`, so it won't alter existing tables. Delete
  `database/noirframe.db` and restart to apply schema changes during
  development.

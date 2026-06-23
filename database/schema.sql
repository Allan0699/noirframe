-- NOIRFRAME platform schema
-- SQLite database. Run automatically by db.py on first launch.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('admin', 'team_lead', 'employee', 'client')),
    company         TEXT,                      -- only meaningful for clients
    title           TEXT,                      -- job title, employees/team leads
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS projects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    category        TEXT NOT NULL DEFAULT 'Video Editing',
    client_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    team_lead_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    description     TEXT,
    budget          REAL DEFAULT 0,
    deadline        TEXT,
    status          TEXT NOT NULL DEFAULT 'Pending'
                        CHECK (status IN ('Pending','In Progress','Review','Revision','Approved','Delivered')),
    progress        INTEGER NOT NULL DEFAULT 0,   -- 0-100, recalculated from tasks
    ai_summary      TEXT,
    ai_estimate     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tasks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    description     TEXT,
    assigned_to     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    priority        TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('Low','Medium','High','Urgent')),
    status          TEXT NOT NULL DEFAULT 'Not Started'
                        CHECK (status IN ('Not Started','Assigned','Working','Under Review','Revision Required','Completed')),
    due_date        TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS task_files (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    task_id         INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
    uploaded_by     INTEGER NOT NULL REFERENCES users(id),
    original_name   TEXT NOT NULL,
    stored_name     TEXT NOT NULL,
    kind            TEXT NOT NULL DEFAULT 'deliverable' CHECK (kind IN ('deliverable','reference')),
    uploaded_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    sender_id       INTEGER NOT NULL REFERENCES users(id),
    body            TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS notifications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    body            TEXT NOT NULL,
    link            TEXT,
    is_read         INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS time_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    clock_in        TEXT NOT NULL DEFAULT (datetime('now')),
    clock_out       TEXT
);

CREATE TABLE IF NOT EXISTS invoices (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    amount          REAL NOT NULL,
    status          TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending','Paid','Overdue')),
    issued_at       TEXT NOT NULL DEFAULT (datetime('now')),
    due_at          TEXT
);

CREATE TABLE IF NOT EXISTS portfolio_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    category        TEXT NOT NULL,
    description     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS testimonials (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name     TEXT NOT NULL,
    role_company    TEXT,
    quote           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contact_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    email           TEXT NOT NULL,
    message         TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_projects_client ON projects(client_id);
CREATE INDEX IF NOT EXISTS idx_projects_team_lead ON projects(team_lead_id);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_messages_project ON messages(project_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);

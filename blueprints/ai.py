from flask import Blueprint, request, jsonify

from db import query_one, query_all, execute
from decorators import role_required, get_current_user
from gemini_client import generate_content, GeminiError
from blueprints.helpers import project_visible_to

bp = Blueprint("ai", __name__, url_prefix="/api/ai")

CHATBOT_SYSTEM_PROMPT = """You are Aria, the friendly virtual assistant for NOIRFRAME,
a premium animation and video editing agency. You help website visitors understand
NOIRFRAME's services (video editing, 2D/3D animation, motion graphics, VFX, CGI,
product ads, social content, YouTube editing, corporate video, brand commercials,
short films, wedding films, AI-assisted production) and pricing tiers (Basic,
Professional, Enterprise, plus custom quotes). Be concise (2-4 sentences), warm, and
professional. If asked something you can't answer (exact pricing, scheduling, contract
specifics), direct the visitor to the contact form or to request a custom quote.
Never invent specific prices or delivery dates."""


@bp.route("/chat", methods=["POST"])
def chat():
    """Public-facing support chatbot on the landing page."""
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message is empty."}), 400
    if len(message) > 2000:
        return jsonify({"error": "Message is too long."}), 400

    try:
        reply = generate_content(message, system_instruction=CHATBOT_SYSTEM_PROMPT, max_output_tokens=300)
    except GeminiError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify({"reply": reply})


@bp.route("/cost-estimate", methods=["POST"])
@role_required("admin", "team_lead")
def cost_estimate():
    """AI-assisted project cost & timeline estimator for internal staff."""
    data = request.get_json(silent=True) or {}
    category = (data.get("category") or "").strip()
    scope = (data.get("scope") or "").strip()
    duration_hint = (data.get("duration_hint") or "").strip()

    if not category or not scope:
        return jsonify({"error": "Category and scope description are required."}), 400

    prompt = f"""A client wants a quote for this project at a video/animation agency.

Service category: {category}
Scope description: {scope}
Client's target turnaround (if given): {duration_hint or "not specified"}

Provide:
1. An estimated budget RANGE in USD (low-high), reasonable for a professional
   creative agency.
2. An estimated timeline range (in business days or weeks).
3. 2-3 sentences of reasoning that a project manager could paste into a quote.
4. Any clarifying questions worth asking the client before finalizing the quote.

Format the answer in short labeled sections, plain text, no markdown tables."""

    try:
        estimate = generate_content(prompt, max_output_tokens=500)
    except GeminiError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify({"estimate": estimate})


@bp.route("/project-summary/<int:project_id>", methods=["POST"])
@role_required("admin", "team_lead")
def project_summary(project_id):
    """Generate an executive summary of a project from its tasks/notes."""
    user = get_current_user()
    project = query_one("SELECT * FROM projects WHERE id = ?", (project_id,))
    if project is None or not project_visible_to(user, project):
        return jsonify({"error": "Project not found."}), 404

    tasks = query_all(
        "SELECT title, status, priority FROM tasks WHERE project_id = ? ORDER BY id",
        (project_id,),
    )
    task_lines = "\n".join(f"- {t['title']} [{t['status']}, priority {t['priority']}]" for t in tasks) or "No tasks yet."

    prompt = f"""Write a brief executive status summary for a client-facing project
update at a video/animation agency.

Project: {project['name']}
Category: {project['category']}
Status: {project['status']}
Progress: {project['progress']}%
Deadline: {project['deadline'] or 'not set'}
Description: {project['description'] or 'not provided'}

Tasks:
{task_lines}

Write 3-5 sentences, professional and reassuring in tone, suitable to show directly
to the client. Mention concrete progress, not generic filler. No markdown formatting."""

    try:
        summary = generate_content(prompt, max_output_tokens=350)
    except GeminiError as exc:
        return jsonify({"error": str(exc)}), 502

    execute("UPDATE projects SET ai_summary = ? WHERE id = ?", (summary, project_id))
    return jsonify({"summary": summary})

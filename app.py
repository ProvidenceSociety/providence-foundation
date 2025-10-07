import os
import csv
import json
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, flash, session, abort
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")  # replace in prod

# ── Admin credentials (set these in your environment on Render) ────────────────
ADMIN_USER = os.environ.get("ADMIN_USER", "admin@example.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")  # set a strong one in prod!

# ── Organization info (edit these) ─────────────────────────────────────────────
ORG_NAME = "Providence Foundation"
ORG_EMAIL = "info@providencefoundation.org"   # TODO: replace
MAILING = {
    "line1": "Providence Foundation",
    "line2": "1234 Classic Ave.",
    "city": "Tulsa",
    "state": "OK",
    "zip": "74137",
}
EIN = "XX-XXXXXXX"  # TODO: replace

# Donation links (Stripe Checkout or Givebutter)
DONATION_LINKS = {
    "pilots":       "https://YOUR_GIVEBUTTER_OR_STRIPE_LINK",  # AI Education
    "teachers":     "https://YOUR_GIVEBUTTER_OR_STRIPE_LINK",
    "houses":       "https://YOUR_GIVEBUTTER_OR_STRIPE_LINK",
    "innovation":   "https://YOUR_GIVEBUTTER_OR_STRIPE_LINK",
    "scholarships": "https://YOUR_GIVEBUTTER_OR_STRIPE_LINK",
    "fifth":        "https://YOUR_GIVEBUTTER_OR_STRIPE_LINK",
}

DATA_DIR = "data"
PROJECTS_JSON = os.path.join(DATA_DIR, "projects.json")

# ── Default project data; will be overridden by projects.json if present ───────
DEFAULT_PROJECTS = [
    {"slug": "ai-education",      "title": "Personalized Education with AI",            "target": 50000,  "raised": 18250, "donation_key": "pilots"},
    {"slug": "teacher-formation", "title": "Teacher Formation & Time Redemption",       "target": 30000,  "raised": 8200,  "donation_key": "teachers"},
    {"slug": "houses-nicaragua",  "title": "Houses for Teachers in Nicaragua",          "target": 120000, "raised": 35500, "donation_key": "houses"},
    {"slug": "fifth-century",     "title": "5th Century Education",                     "target": 40000,  "raised": 6100,  "donation_key": "fifth"},
]

# ── Simple JSON persistence for projects ───────────────────────────────────────
def load_projects():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.isfile(PROJECTS_JSON):
        with open(PROJECTS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    # seed file with defaults the first time
    save_projects(DEFAULT_PROJECTS)
    return DEFAULT_PROJECTS

def save_projects(projects):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PROJECTS_JSON, "w", encoding="utf-8") as f:
        json.dump(projects, f, indent=2)

PROJECTS = load_projects()

def get_project(slug):
    for p in PROJECTS:
        if p["slug"] == slug:
            return p
    return None

# ── Globals available to all templates ─────────────────────────────────────────
@app.context_processor
def inject_globals():
    return dict(
        ORG_NAME=ORG_NAME,
        ORG_EMAIL=ORG_EMAIL,
        MAILING=MAILING,
        EIN=EIN,
        DONATION_LINKS=DONATION_LINKS,
        IS_ADMIN=session.get("is_admin", False),
    )

# ── Basic site routes ─────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/projects")
def projects():
    # compute percents for the public projects grid if you want later
    return render_template("projects.html")

@app.route("/team")
def team():
    bios = [
        {"name": "FIRST LAST", "role": "Founder & Executive Director",
         "bio": "One to three sentences on vocation, track record, and calling to this work.",
         "img": "headshots/founder.jpg"},
        {"name": "FIRST LAST", "role": "Board Chair",
         "bio": "Brief background, professional expertise, and alignment with the mission.",
         "img": "headshots/chair.jpg"},
        {"name": "FIRST LAST", "role": "Treasurer",
         "bio": "Financial stewardship experience and commitment to transparency.",
         "img": "headshots/treasurer.jpg"},
        {"name": "FIRST LAST", "role": "Secretary",
         "bio": "Governance, administration, and documentation support.",
         "img": "headshots/secretary.jpg"},
        {"name": "FIRST LAST", "role": "Advisor",
         "bio": "Counsel in education/theology/technology/philanthropy, etc.",
         "img": "headshots/advisor.jpg"},
        {"name": "FIRST LAST", "role": "Advisor",
         "bio": "Area of counsel and brief experience.",
         "img": "headshots/advisor2.jpg"},
    ]
    return render_template("team.html", bios=bios)

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not message:
            flash("Please fill out name, email, and message.", "error")
            return redirect(url_for("contact"))

        os.makedirs(DATA_DIR, exist_ok=True)
        csv_path = os.path.join(DATA_DIR, "contact_submissions.csv")
        file_exists = os.path.isfile(csv_path)

        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["timestamp", "name", "email", "message"])
            writer.writerow([datetime.utcnow().isoformat(), name, email, message])

        flash("Thanks for your message—we’ll get back to you soon.", "success")
        return redirect(url_for("contact"))

    return render_template("contact.html")

# ── Project detail pages ───────────────────────────────────────────────────────
@app.route("/projects/ai-education")
def project_ai():
    return render_template("projects/ai.html")

@app.route("/projects/teacher-formation")
def project_teacher():
    return render_template("projects/teacher.html")

@app.route("/projects/houses-nicaragua")
def project_houses():
    return render_template("projects/houses.html")

@app.route("/projects/5th-century")
def project_5th():
    return render_template("projects/5th.html")

# ── Donor Dashboard (uses PROJECTS for progress bars) ─────────────────────────
@app.route("/dashboard")
def dashboard():
    projects_view = []
    for p in PROJECTS:
        target = max(int(p.get("target", 0)) or 1, 1)
        raised = int(p.get("raised", 0) or 0)
        pct = min(100, round((raised / target) * 100))
        projects_view.append({**p, "percent": pct, "target": target, "raised": raised})
    return render_template("dashboard.html", projects=projects_view)

# ── Admin auth helpers ────────────────────────────────────────────────────────
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if email.lower() == ADMIN_USER.lower() and password == ADMIN_PASSWORD:
            session["is_admin"] = True
            session["admin_email"] = email
            flash("Welcome, admin.", "success")
            dest = request.args.get("next") or url_for("admin_home")
            return redirect(dest)
        else:
            flash("Invalid credentials.", "error")
            return redirect(url_for("admin_login"))
    return render_template("admin/login.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("Signed out.", "success")
    return redirect(url_for("home"))

# ── Admin dashboard ───────────────────────────────────────────────────────────
@app.route("/admin")
@admin_required
def admin_home():
    return render_template("admin/dashboard.html", projects=PROJECTS)

# Edit a project
@app.route("/admin/projects/<slug>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_project(slug):
    project = get_project(slug)
    if not project:
        abort(404)
    if request.method == "POST":
        project["title"] = request.form.get("title", project["title"]).strip() or project["title"]
        try:
            project["target"] = int(float(request.form.get("target", project["target"])))
            project["raised"] = int(float(request.form.get("raised", project["raised"])))
        except ValueError:
            flash("Target and Raised must be numbers.", "error")
            return redirect(url_for("admin_edit_project", slug=slug))

        # optional: allow changing the donation link key or a custom URL
        donation_key = request.form.get("donation_key", "").strip()
        custom_link = request.form.get("donation_url", "").strip()
        if donation_key:
            project["donation_key"] = donation_key
        if custom_link:
            project["donation_url"] = custom_link  # stored per project

        save_projects(PROJECTS)
        flash("Project updated.", "success")
        return redirect(url_for("admin_home"))

    # Build current donate URL (key or per-project override)
    donate_url = project.get("donation_url") or DONATION_LINKS.get(project.get("donation_key", ""), "")
    return render_template("admin/edit_project.html",
                           project=project,
                           donation_keys=sorted(DONATION_LINKS.keys()),
                           donate_url=donate_url)

# ── Dev server ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)

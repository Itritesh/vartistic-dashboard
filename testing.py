"""
Vartistic dashboard checker. Lives outside the app, only reads index.html.

Usage:
    python testing.py                     # looks for index.html next to this file
    python testing.py --app path/to/index.html
    python testing.py --headed            # watch the browser run

Full browser run needs Playwright (one time):
    pip install playwright
    playwright install chromium
Without Playwright the script still runs the file checks.
GitHub calls go to the real GitHub API when you are online. Offline, the app
saves the account as "unverified", and the test accepts either result.
"""
import argparse, functools, http.server, pathlib, re, sys, threading

p = argparse.ArgumentParser()
p.add_argument("--app", default=str(pathlib.Path(__file__).with_name("index.html")))
p.add_argument("--headed", action="store_true")
args = p.parse_args()

app = pathlib.Path(args.app).resolve()
results = []


def check(name, ok, note=""):
    results.append(ok)
    print(("PASS  " if ok else "FAIL  ") + name + (f"  ({note})" if note else ""))


# ---------- 1. file checks ----------
if not app.exists():
    sys.exit(f"Cannot find {app}")
src = app.read_text(encoding="utf8")

must = {
    "admin email login": "setup?'setup':'login'",
    "team login": "value=\"member\"",
    "localStorage data": "localStorage.setItem(K",
    "GitHub API": "api.github.com",
    "file upload, any type": "type=\"file\" multiple",
    "status chart": "class=\"donut\"",
    "calendar": "function calV",
    "leaderboard": "function boardV",
    "client updates": "function updatesV",
    "send back feedback": "function feedbackV",
    "daily project updates": "data-form=\"daily\"",
    "theme switch": "data-theme=light",
    "logo embedded": "class=\"logo",
    "responsive rules": "@media(max-width:480px)",
}
for label, needle in must.items():
    check("file has " + label, needle in src)
check("no external JS libraries", not re.search(r"<script[^>]+src=", src))
check("no browser-storage misuse of cookies", "document.cookie" not in src)

# ---------- 2. browser run ----------
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("\nPlaywright is not installed, so the browser checks were skipped.")
    print("Run: pip install playwright && playwright install chromium")
    sys.exit(0 if all(results) else 1)

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k):
        pass


handler = functools.partial(Quiet, directory=str(app.parent))
server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{server.server_address[1]}/{app.name}"

ADMIN, ADMIN_PW = "boss@vartistic.com", "admin123"
MEMBER, MEMBER_PW = "ritesh@vartistic.com", "welcome123"
TEAMMATE = "sarib@vartistic.com"

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=not args.headed)
    ctx = browser.new_context(viewport={"width": 1280, "height": 860})
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    def nav(tab):
        page.click(f"[data-act=nav][data-v={tab}]")
        page.wait_for_timeout(120)

    def login(email, pw_, role):
        page.check(f"[name=role][value={role}]", force=True)
        page.fill("[data-form=login] [name=email]", email)
        page.fill("[data-form=login] [name=pw]", pw_)
        page.click("[data-form=login] button.btn")
        page.wait_for_selector(".shell")

    def connect_github(user):
        page.wait_for_selector("form[data-form=gh]")
        page.fill("[data-form=gh] [name=user]", user)
        page.click("[data-form=gh] button.btn")
        page.wait_for_selector("form[data-form=gh]", state="detached", timeout=15000)

    def db():
        return page.evaluate("JSON.parse(localStorage.getItem('vartistic.v1'))")

    page.goto(url)
    check("login page loads with logo", page.locator(".card-auth img.logo").count() == 1)

    # admin setup
    page.fill("[data-form=setup] [name=email]", ADMIN)
    page.fill("[data-form=setup] [name=pw]", ADMIN_PW)
    page.fill("[data-form=setup] [name=pw2]", ADMIN_PW)
    page.click("[data-form=setup] button.btn")
    page.wait_for_selector(".shell")
    check("admin account created and logged in", True)
    check("home shows 5 candidates", page.locator("[data-k=candidates] b").get_attribute("data-count") == "5")
    check("status chart drawn", page.locator("svg.donut").count() == 1)

    for tab in ["projects", "tasks", "feedback", "updates", "cal", "board", "team", "home"]:
        nav(tab)
        check(f"tab opens: {tab}", page.locator(".view").inner_text().strip() != "")

    # theme
    page.click("[data-act=theme]")
    check("light theme switches on", page.evaluate("document.documentElement.dataset.theme") == "light")
    page.click("[data-act=theme]")

    # project + task + update
    nav("projects")
    page.click("[data-act=newproj]")
    page.fill("[data-form=project] [name=name]", "Zenith site")
    page.fill("[data-form=project] [name=repo]", "https://github.com/octocat/Hello-World")
    page.click("[data-form=project] button.btn")
    page.wait_for_timeout(200)
    check("project created", len(db()["projects"]) == 1)
    project_id = db()["projects"][0]["id"]

    nav("tasks")
    page.click("[data-act=newtask]")
    page.fill("[data-form=task] [name=title]", "Landing page")
    page.select_option("[data-form=task] [name=project]", project_id)
    page.check("#all")
    page.click("[data-form=task] button.btn")
    page.wait_for_timeout(200)
    check("task shared with all 5 members", len(db()["tasks"]) == 5)
    check("members auto-added to the project", len(db()["projects"][0]["members"]) == 5)

    nav("updates")
    page.click("[data-act=newupd]")
    page.fill("[data-form=upd] [name=title]", "Client wants a new logo")
    page.fill("[data-form=upd] [name=text]", "Use the black version")
    page.click("[data-form=upd] button.btn")
    page.wait_for_timeout(200)
    check("client update posted", len(db()["updates"]) == 1)

    # persistence
    page.reload()
    page.wait_for_selector(".shell")
    check("data and login survive a reload", len(db()["tasks"]) == 5)
    page.click("[data-act=out]")

    # member flow
    login(MEMBER, MEMBER_PW, "member")
    check("GitHub connect is required after login", page.locator("form[data-form=gh]").count() == 1)
    connect_github("octocat")
    gh = db()["members"][0]["gh"]
    check("GitHub account saved", bool(gh and gh["user"]))
    check("new client update badge shown", page.locator(".nv .bd").count() == 1)

    nav("tasks")
    page.click("[data-act=set][data-v=completed]")
    check("upload area appears when completed", page.locator(".up").count() == 1)
    page.set_input_files("input[data-up]", {"name": "brief.pdf", "mimeType": "application/pdf", "buffer": b"%PDF-1.4 test"})
    page.wait_for_selector(".file")
    check("file uploaded", page.locator(".file").count() == 1)
    page.fill("input[data-repo]", "https://github.com/octocat/Hello-World")
    page.dispatch_event("input[data-repo]", "change")
    page.click("[data-act=share]")
    page.wait_for_timeout(200)
    done = [t for t in db()["tasks"] if t["status"] == "completed"][0]
    check("work saved and shared with the team", done["share"] == "team")

    nav("projects")
    page.click("[data-act=proj]")
    page.fill("[data-form=daily] [name=text]", "Built the hero section")
    page.check("[data-form=daily] [name=commit]")
    page.click("[data-form=daily] button.btn")
    page.wait_for_timeout(200)
    check("daily update saved", len(db()["dailies"]) == 1)
    nav("board")
    check("leaderboard counts the streak", "1 day streak" in page.locator(".view").inner_text())
    nav("cal")
    check("calendar highlights today", page.locator(".cd.today").count() == 1)
    page.click("[data-act=out]")

    # teammate: read only
    login(TEAMMATE, MEMBER_PW, "member")
    connect_github("sarib-dev-test")
    body = page.locator(".view").inner_text()
    check("teammate sees shared work on their dashboard", "Landing page" in body and "Shared by teammates" in body)
    page.click("[data-act=view]")
    page.wait_for_selector(".sheet")
    sheet = page.locator(".sheet").inner_text()
    check("teammate view is read only", "Read only" in sheet and page.locator("[data-act=approve]").count() == 0)
    page.keyboard.press("Escape")
    page.click("[data-act=out]")

    # admin review
    login(ADMIN, ADMIN_PW, "admin")
    nav("tasks")
    page.select_option("[data-f=st]", "completed")
    page.click("[data-act=view]")
    page.wait_for_selector("[data-act=rework]")
    page.click("[data-act=rework]")
    check("send back needs feedback", all(t["review"] != "rework" for t in db()["tasks"]))
    page.fill("#rn", "Fix the hero spacing")
    page.click("[data-act=rework]")
    page.wait_for_timeout(200)
    check("task sent back with feedback", any(t["review"] == "rework" and t["feedback"] for t in db()["tasks"]))
    nav("feedback")
    check("feedback shows in Sent back section", "Fix the hero spacing" in page.locator(".view").inner_text())
    nav("team")
    page.click("[data-act=person] >> nth=0")
    check("admin can open a member dashboard", "Back to team" in page.locator(".view").inner_text())

    # responsive
    for w, h, label in [(360, 740, "phone"), (820, 1100, "tablet"), (1600, 900, "desktop")]:
        page.set_viewport_size({"width": w, "height": h})
        page.wait_for_timeout(150)
        wide = page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
        check(f"no sideways scrolling on {label}", not wide)

    check("no JavaScript errors in the browser", not errors, "; ".join(errors[:2]))
    browser.close()
server.shutdown()

passed = sum(results)
print(f"\n{passed}/{len(results)} checks passed")
sys.exit(0 if passed == len(results) else 1)

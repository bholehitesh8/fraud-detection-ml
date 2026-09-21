import urllib.request
import urllib.parse
import http.cookiejar
import re
import json

BASE_URL = "http://127.0.0.1:5000"

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

print("================================================================================")
print("     VERIFYING ENTERPRISE CHARCOAL + EMERALD + TEAL + WHITE DESIGN SYSTEM")
print("================================================================================")

# 1. Verify CSS delivery and complete blue absence
print("\n[1] Verifying /static/css/style.css delivery and zero-blue guarantee...")
req = urllib.request.Request(f"{BASE_URL}/static/css/style.css")
with opener.open(req) as resp:
    assert resp.status == 200, f"CSS failed: {resp.status}"
    css_content = resp.read().decode("utf-8")
    assert len(css_content) > 50000, "CSS file truncated"

blue_regex = re.compile(r'#(?:3b82f6|2563eb|007bff|0d6efd|1d4ed8|38bdf8|60a5fa)', re.IGNORECASE)
css_blue_matches = blue_regex.findall(css_content)
assert len(css_blue_matches) == 0, f"Found lingering blue in CSS: {css_blue_matches}"

# Check design tokens present in CSS
for token in ["#111827", "#1F2937", "#374151", "#10B981", "#14B8A6", "#F8FAFC", "#E2E8F0"]:
    assert token.lower() in css_content.lower(), f"Missing design token {token} in style.css"

print(" -> style.css verified: 0 blue references, all Charcoal/Emerald/Teal tokens active.")

# 2. Verify Login Page
print("\n[2] Verifying Login Page (Split Layout & Zero Blue)...")
with opener.open(f"{BASE_URL}/login") as resp:
    assert resp.status == 200, f"Login GET failed: {resp.status}"
    login_html = resp.read().decode("utf-8")

assert "ai-login-wrapper" in login_html, "Missing split login wrapper"
assert "ai-branding-pane" in login_html, "Missing AI branding left pane"
assert "ai-login-card" in login_html, "Missing right login card"
assert "FraudGuard AI" in login_html, "Missing brand title"
assert "Continue with Google" in login_html, "Missing Google login"
assert "Admin Demo" in login_html, "Missing Admin Demo profile"
assert "Analyst Demo" in login_html, "Missing Analyst Demo profile"

login_blue_matches = blue_regex.findall(login_html)
assert len(login_blue_matches) == 0, f"Found blue hex in login.html: {login_blue_matches}"
print(" -> Login Page verified: Split layout, Google OAuth, 0 blue hex occurrences.")

# 3. Log in as Admin
print("\n[3] Authenticating as Admin...")
login_payload = urllib.parse.urlencode({
    "identifier": "admin",
    "password": "AdminPassword123!"
}).encode("utf-8")

login_req = urllib.request.Request(f"{BASE_URL}/login", data=login_payload, method="POST")
with opener.open(login_req) as resp:
    assert resp.status in (200, 302), f"Login post failed: {resp.status}"
print(" -> Successfully authenticated as Admin.")

# 4. Verify Dashboard HTML
print("\n[4] Verifying Dashboard (Fraud Intelligence Center)...")
with opener.open(f"{BASE_URL}/dashboard") as resp:
    assert resp.status == 200, f"Dashboard GET failed: {resp.status}"
    dash_html = resp.read().decode("utf-8")

# Required UI sections
assert "Fraud Intelligence Center" in dash_html, "Missing Fraud Intelligence Center title"
assert "AI-powered transaction security monitoring" in dash_html, "Missing subtitle"
assert "SYSTEM SECURITY" in dash_html, "Missing SYSTEM SECURITY probe panel"
assert "AI MODEL" in dash_html, "Missing AI MODEL card"
assert "Model Ready" in dash_html, "Missing Model Ready indicator"
assert "chartFraudVsSafe" in dash_html, "Missing chartFraudVsSafe"
assert "chartFraudTrend" in dash_html, "Missing chartFraudTrend"
assert "chartCurrencyDist" in dash_html, "Missing chartCurrencyDist"
assert "chartRiskDist" in dash_html, "Missing chartRiskDist"
assert "kpiTotal" in dash_html, "Missing KPI total transactions"
assert "kpiFraud" in dash_html, "Missing KPI fraud detected"
assert "kpiLegit" in dash_html, "Missing KPI safe transactions"
assert "kpiRate" in dash_html, "Missing KPI fraud rate"

# Verify Sidebar navigation labels
for label in ["Dashboard", "Make Prediction", "Prediction History", "Analytics", "Model Information", "Admin", "Audit Logs"]:
    assert label in dash_html, f"Missing sidebar item: {label}"

dash_blue_matches = blue_regex.findall(dash_html)
assert len(dash_blue_matches) == 0, f"Found blue hex in dashboard.html: {dash_blue_matches}"
print(" -> Dashboard verified: All KPI cards, charts, system security probes, and sidebar items confirmed.")

# 5. Verify /predict, /history, /analytics, /admin, /about
pages_to_test = [
    ("/predict", "Make Prediction"),
    ("/history", "Prediction History"),
    ("/analytics", "Analytics"),
    ("/admin", "Admin Operations"),
    ("/about", "Architecture"),
]

print("\n[5] Verifying all remaining routes and views...")
for route, expected_text in pages_to_test:
    with opener.open(f"{BASE_URL}{route}") as resp:
        assert resp.status == 200, f"Route {route} failed with {resp.status}"
        body = resp.read().decode("utf-8")
        assert expected_text in body, f"Route {route} missing expected text '{expected_text}'"
        matches = blue_regex.findall(body)
        assert len(matches) == 0, f"Found blue in route {route}: {matches}"
        print(f" -> {route}: OK (200, zero blue, verified content)")

print("\n================================================================================")
print(" [SUCCESS] ALL VISUAL THEME & DESIGN SYSTEM CHECKS PASSED WITH ZERO REGRESSIONS!")
print("================================================================================")

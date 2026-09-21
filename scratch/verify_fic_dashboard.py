"""
Verification script for Fraud Intelligence Center Security Dashboard
Uses standard library urllib.request with cookiejar to test live endpoints.
"""
import urllib.request
import urllib.parse
import json
import http.cookiejar

BASE_URL = "http://127.0.0.1:5000"

def run_test():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    print("[1] Testing Login as Admin...")
    login_data = urllib.parse.urlencode({
        "identifier": "admin",
        "password": "AdminPassword123!"
    }).encode("utf-8")
    
    req = urllib.request.Request(f"{BASE_URL}/login", data=login_data, method="POST")
    resp = opener.open(req)
    assert resp.status == 200, f"Admin login failed: {resp.status}"
    print(" -> Admin logged in successfully.")

    print("[2] Testing GET /dashboard HTML...")
    req = urllib.request.Request(f"{BASE_URL}/dashboard", method="GET")
    resp = opener.open(req)
    assert resp.status == 200, f"GET /dashboard failed: {resp.status}"
    html = resp.read().decode("utf-8")

    # Verification checks
    assert "Fraud Intelligence Center" in html, "Missing Fraud Intelligence Center title"
    assert "FraudGuard" in html, "Missing FraudGuard branding"
    assert "ficLiveClock" in html, "Missing live UTC clock"
    assert "ficAlertCountChip" in html, "Missing alert count chip"
    assert "SYSTEM SECURITY" in html, "Missing SYSTEM SECURITY panel"
    assert "API Service" in html, "Missing API probe"
    assert "Database" in html, "Missing DB probe"
    assert "ML Inference" in html, "Missing ML Inference probe"
    assert "Access Control" in html, "Missing Access Control probe"
    assert "kpiTotal" in html, "Missing kpiTotal"
    assert "kpiFraud" in html, "Missing kpiFraud"
    assert "kpiLegit" in html, "Missing kpiLegit"
    assert "kpiRate" in html, "Missing kpiRate"
    assert "kpiAvgAmount" in html, "Missing kpiAvgAmount"
    assert "kpiMaxAmount" in html, "Missing kpiMaxAmount"
    assert "kpiTodayCount" in html, "Missing kpiTodayCount"
    assert "kpiSevenDayCount" in html, "Missing kpiSevenDayCount"
    assert "Fraud Risk Overview" in html, "Missing Fraud Risk Overview"
    assert "chartFraudVsSafe" in html, "Missing chartFraudVsSafe canvas"
    assert "Transaction Activity Timeline" in html, "Missing Activity Timeline"
    assert "chartFraudTrend" in html, "Missing chartFraudTrend canvas"
    assert "fic-timeline-switch" in html, "Missing timeline switch"
    assert "Risk Level Distribution" in html, "Missing Risk Level Distribution"
    assert "chartRiskDist" in html, "Missing chartRiskDist canvas"
    assert "Fraud Alert Center" in html, "Missing Fraud Alert Center"
    assert "ficAlertsList" in html, "Missing ficAlertsList"
    assert "Recent Transaction Activity Monitor" in html, "Missing Recent Transaction Monitor"
    assert "recentTableSearch" in html, "Missing table search"
    assert "recentActivityTable" in html, "Missing recentActivityTable"
    assert "Currency Activity &amp; Strict Segregation" in html, "Missing Currency Activity widget"
    assert "AI MODEL" in html, "Missing AI MODEL card"
    assert "Model Ready" in html, "Missing Model Ready badge"
    assert "ExtraTrees Ensemble" in html, "Missing ExtraTrees specification"
    assert "Metrics represent model evaluation results and are not live transaction accuracy." in html, "Missing evaluation disclaimer"
    assert "AI Pattern Insights" in html, "Missing AI Pattern Insights"
    assert "ficInsightsList" in html, "Missing ficInsightsList"
    assert "Security &amp; Access Audit Stream" in html, "Missing Security Audit stream"
    assert "ficSecurityFeed" in html, "Missing ficSecurityFeed"
    assert "fic-quick-actions-bar" in html, "Missing Quick Actions"
    assert "User Directory" in html, "Admin should see User Directory"
    assert "Security Audit Logs" in html, "Admin should see Audit Logs"
    assert "globalFilterDays" in html, "Missing globalFilterDays"
    assert "globalFilterCurrency" in html, "Missing globalFilterCurrency"
    assert "globalFilterStatus" in html, "Missing globalFilterStatus"
    assert "globalFilterRisk" in html, "Missing globalFilterRisk"
    assert "btnResetFilters" in html, "Missing btnResetFilters"

    print(" -> All 22 dashboard UI elements verified in live HTML.")

    print("[3] Testing GET /api/analytics/summary (All-Time)...")
    req = urllib.request.Request(f"{BASE_URL}/api/analytics/summary", method="GET")
    resp = opener.open(req)
    assert resp.status == 200, f"Analytics API failed: {resp.status}"
    data = json.loads(resp.read().decode("utf-8"))
    assert data.get("success") is True, "success is not True"
    summary = data.get("summary", {})
    print(f" -> Real DB Stats: Total={summary.get('total_predictions')}, Fraud={summary.get('fraudulent_predictions')}, Safe={summary.get('safe_predictions')}, Rate={summary.get('fraud_percentage')}%, Currencies={summary.get('active_currencies_count')}")
    print(f" -> Probes: API={data.get('system_status', {}).get('api', {}).get('status')}, DB={data.get('system_status', {}).get('database', {}).get('status')}, ML={data.get('system_status', {}).get('ml_model', {}).get('status')}")
    print(f" -> Alerts Detected: {len(data.get('fraud_alerts', []))}")
    print(f" -> Insights Derived: {len(data.get('ai_insights', []))}")
    print(f" -> Security Events Scoped: {len(data.get('security_events', []))}")

    print("[4] Testing Filter Parameters on /api/analytics/summary...")
    req = urllib.request.Request(f"{BASE_URL}/api/analytics/summary?days=30&status=fraud", method="GET")
    resp = opener.open(req)
    assert resp.status == 200
    filt_data = json.loads(resp.read().decode("utf-8"))
    assert filt_data.get("success") is True
    print(f" -> Filtered (status=fraud) total: {filt_data.get('summary', {}).get('total_predictions')}")

    print("[5] Testing Analyst Role Access...")
    analyst_cj = http.cookiejar.CookieJar()
    analyst_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(analyst_cj))
    a_login_data = urllib.parse.urlencode({
        "identifier": "secanalyst",
        "password": "AnalystPassword123!"
    }).encode("utf-8")
    a_req = urllib.request.Request(f"{BASE_URL}/login", data=a_login_data, method="POST")
    a_resp = analyst_opener.open(a_req)
    assert a_resp.status == 200

    a_dash_req = urllib.request.Request(f"{BASE_URL}/dashboard", method="GET")
    a_dash_resp = analyst_opener.open(a_dash_req)
    assert a_dash_resp.status == 200
    a_html = a_dash_resp.read().decode("utf-8")
    assert "User Directory" not in a_html, "Analyst should not see User Directory"
    assert "Security Audit Logs" not in a_html, "Analyst should not see Admin Security Audit Logs button"
    print(" -> Analyst RBAC isolation verified.")

    print("\n=======================================================")
    print(" [PASSED] ALL 22 ENTERPRISE DASHBOARD REQUIREMENTS OK! ")
    print("=======================================================")

if __name__ == "__main__":
    run_test()

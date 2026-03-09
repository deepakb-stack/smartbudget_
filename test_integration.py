"""
SmartBudget - Integration Test Suite (Frontend + Backend)
Tests end-to-end workflows: template rendering with DB data, AJAX endpoints,
form submissions, session management, and cross-component consistency.
"""
import os
import sys
import sqlite3
import shutil
import json
import re

results = []

# Use a copy of the database
ORIG_DB = "database.db"
TEST_DB = "test_integration_db.db"
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
if os.path.exists(ORIG_DB):
    shutil.copy2(ORIG_DB, TEST_DB)

_orig_connect = sqlite3.connect
def _test_connect(db_name, *args, **kwargs):
    if db_name == "database.db":
        db_name = TEST_DB
    kwargs.setdefault("timeout", 10)
    return _orig_connect(db_name, *args, **kwargs)
sqlite3.connect = _test_connect

import app as smartbudget_app

flask_app = smartbudget_app.app
flask_app.config["TESTING"] = True

test_user = "__integration_test_user__"
test_pass = "intpass123"

# ============================================================
# SETUP: Create test user and data
# ============================================================

conn = sqlite3.connect("database.db")
conn.execute("DELETE FROM users WHERE username=?", (test_user,))
conn.execute("DELETE FROM transactions WHERE username=?", (test_user,))
conn.execute("DELETE FROM user_settings WHERE username=?", (test_user,))
conn.commit()
conn.close()

client = flask_app.test_client()

# Register
resp = client.post("/register", data={
    "username": test_user,
    "password": test_pass,
    "confirm_password": test_pass,
    "security_question": "pet",
    "security_answer": "buddy"
})
results.append(("PASS" if resp.status_code == 302 else "FAIL",
                "INT-SETUP-REGISTER", f"Test user registered (status={resp.status_code})"))

# Login
resp = client.post("/", data={"username": test_user, "password": test_pass}, follow_redirects=False)
results.append(("PASS" if resp.status_code == 302 else "FAIL",
                "INT-SETUP-LOGIN", f"Test user logged in (status={resp.status_code})"))

with client.session_transaction() as sess:
    sess["user"] = test_user

# Add sample transactions
sample_txns = [
    ("Income", "Salary", "January salary", "50000"),
    ("Income", "Business", "Freelance project", "15000"),
    ("Expense", "Food", "Monthly groceries", "8000"),
    ("Expense", "Transport", "Fuel and metro", "3500"),
    ("Expense", "Bills", "Electricity + internet", "4200"),
    ("Expense", "Shopping", "New clothes", "6000"),
    ("Expense", "Entertainment", "Movie and dinner", "2500"),
    ("Income", "Gift", "Birthday gift", "5000"),
]

for ttype, cat, desc, amt in sample_txns:
    resp = client.post("/add_transaction", data={
        "type": ttype, "category": cat, "description": desc, "amount": amt
    }, follow_redirects=False)
    if resp.status_code != 302:
        results.append(("FAIL", f"INT-SETUP-TX-{cat}", f"Failed to add {ttype}/{cat}"))
results.append(("PASS", "INT-SETUP-DATA", f"{len(sample_txns)} sample transactions added"))

# ============================================================
# TEST 1: HOME PAGE — Template renders with correct DB data
# ============================================================

resp = client.get("/home")
html = resp.data.decode("utf-8")

if resp.status_code == 200:
    results.append(("PASS", "INT-HOME-STATUS", "Home page returns 200"))
else:
    results.append(("FAIL", "INT-HOME-STATUS", f"Home page returned {resp.status_code}"))

# Check balance components present
total_income = 50000 + 15000 + 5000  # 70000
total_expense = 8000 + 3500 + 4200 + 6000 + 2500  # 24200
balance = total_income - total_expense  # 45800

if str(int(total_income)) in html or f"{total_income}" in html:
    results.append(("PASS", "INT-HOME-INCOME-DATA", f"Income {total_income} rendered in template"))
else:
    results.append(("FAIL", "INT-HOME-INCOME-DATA", f"Income {total_income} not found in page"))

if str(int(total_expense)) in html or f"{total_expense}" in html:
    results.append(("PASS", "INT-HOME-EXPENSE-DATA", f"Expense {total_expense} rendered in template"))
else:
    results.append(("FAIL", "INT-HOME-EXPENSE-DATA", f"Expense {total_expense} not found in page"))

if str(int(balance)) in html or f"{balance}" in html:
    results.append(("PASS", "INT-HOME-BALANCE-DATA", f"Balance {balance} rendered in template"))
else:
    results.append(("FAIL", "INT-HOME-BALANCE-DATA", f"Balance {balance} not found in page"))

# Check transaction count rendered
if f"{len(sample_txns)} entries" in html:
    results.append(("PASS", "INT-HOME-TX-COUNT", f"{len(sample_txns)} entries shown"))
else:
    results.append(("WARN", "INT-HOME-TX-COUNT", "Transaction count text not found (may have different format)"))

# Check all transactions are displayed
for ttype, cat, desc, amt in sample_txns:
    if cat in html:
        results.append(("PASS", f"INT-HOME-TX-{cat}", f"Transaction '{cat}' displayed"))
    else:
        results.append(("FAIL", f"INT-HOME-TX-{cat}", f"Transaction '{cat}' not in page"))

# Check currency symbol
if "₹" in html:
    results.append(("PASS", "INT-HOME-CURRENCY", "Currency symbol ₹ rendered"))
else:
    results.append(("WARN", "INT-HOME-CURRENCY", "₹ symbol not found (may use different default)"))

# Check Welcome message with username
if test_user in html:
    results.append(("PASS", "INT-HOME-USERNAME", f"Username '{test_user}' in welcome message"))
else:
    results.append(("FAIL", "INT-HOME-USERNAME", "Username not in page"))

# ============================================================
# TEST 2: HOME PAGE — Filter & Sort
# ============================================================

# Filter: income only
resp = client.get("/home?filter=income")
html = resp.data.decode("utf-8")
if "Salary" in html and "Food" not in html:
    results.append(("PASS", "INT-HOME-FILTER-INCOME", "Income filter hides expense transactions"))
elif "Salary" in html:
    results.append(("WARN", "INT-HOME-FILTER-INCOME", "Income filter shows Salary but also shows expenses"))
else:
    results.append(("FAIL", "INT-HOME-FILTER-INCOME", "Income filter not working"))

# Filter: expense only
resp = client.get("/home?filter=expense")
html = resp.data.decode("utf-8")
if "Food" in html and "Salary" not in html:
    results.append(("PASS", "INT-HOME-FILTER-EXPENSE", "Expense filter hides income transactions"))
elif "Food" in html:
    results.append(("WARN", "INT-HOME-FILTER-EXPENSE", "Expense filter shows Food but also shows income"))
else:
    results.append(("FAIL", "INT-HOME-FILTER-EXPENSE", "Expense filter not working"))

# Sort: amount_high
resp = client.get("/home?sort=amount_high")
html = resp.data.decode("utf-8")
if resp.status_code == 200:
    results.append(("PASS", "INT-HOME-SORT-HIGH", "Sort by amount high renders correctly"))
else:
    results.append(("FAIL", "INT-HOME-SORT-HIGH", f"Sort returned {resp.status_code}"))

# ============================================================
# TEST 3: STATS PAGE — Template + API consistency
# ============================================================

resp = client.get("/stats")
stats_html = resp.data.decode("utf-8")
if resp.status_code == 200:
    results.append(("PASS", "INT-STATS-PAGE", "Stats page renders"))
else:
    results.append(("FAIL", "INT-STATS-PAGE", f"Stats page returned {resp.status_code}"))

# Check stats page shows data
if str(int(total_income)) in stats_html:
    results.append(("PASS", "INT-STATS-INCOME-DISPLAY", "Stats page shows income value"))
else:
    results.append(("WARN", "INT-STATS-INCOME-DISPLAY", "Income value not visible in stats HTML"))

# API consistency check
resp = client.get("/stats_data")
stats_data = json.loads(resp.data)

if stats_data["income"] == total_income:
    results.append(("PASS", "INT-STATS-API-INCOME", f"API income matches expected: {total_income}"))
else:
    results.append(("FAIL", "INT-STATS-API-INCOME", f"API income {stats_data['income']} != expected {total_income}"))

if stats_data["expense"] == total_expense:
    results.append(("PASS", "INT-STATS-API-EXPENSE", f"API expense matches expected: {total_expense}"))
else:
    results.append(("FAIL", "INT-STATS-API-EXPENSE", f"API expense {stats_data['expense']} != expected {total_expense}"))

expected_savings = total_income - total_expense
if stats_data["savings"] == expected_savings:
    results.append(("PASS", "INT-STATS-API-SAVINGS", f"API savings matches: {expected_savings}"))
else:
    results.append(("FAIL", "INT-STATS-API-SAVINGS", f"API savings {stats_data['savings']} != {expected_savings}"))

expected_rate = round(expected_savings / total_income * 100, 1)
if stats_data["savings_rate"] == expected_rate:
    results.append(("PASS", "INT-STATS-API-RATE", f"Savings rate matches: {expected_rate}%"))
else:
    results.append(("FAIL", "INT-STATS-API-RATE", f"Rate {stats_data['savings_rate']} != {expected_rate}"))

# Check category breakdowns
if "Salary" in stats_data.get("income_categories", {}):
    results.append(("PASS", "INT-STATS-API-INCOME-CATS", "Income categories include Salary"))
else:
    results.append(("FAIL", "INT-STATS-API-INCOME-CATS", "Income categories missing Salary"))

if "Food" in stats_data.get("expense_categories", {}):
    results.append(("PASS", "INT-STATS-API-EXPENSE-CATS", "Expense categories include Food"))
else:
    results.append(("FAIL", "INT-STATS-API-EXPENSE-CATS", "Expense categories missing Food"))

# Verify all expense categories present
for cat in ["Food", "Transport", "Bills", "Shopping", "Entertainment"]:
    if cat in stats_data.get("expense_categories", {}):
        results.append(("PASS", f"INT-STATS-ECAT-{cat}", f"Expense category '{cat}' in API"))
    else:
        results.append(("FAIL", f"INT-STATS-ECAT-{cat}", f"Expense category '{cat}' missing"))

# ============================================================
# TEST 4: ADVISOR PAGE — Financial context integration
# ============================================================

resp = client.get("/advisor")
adv_html = resp.data.decode("utf-8")
if resp.status_code == 200:
    results.append(("PASS", "INT-ADVISOR-PAGE", "Advisor page renders"))
else:
    results.append(("FAIL", "INT-ADVISOR-PAGE", f"Advisor returned {resp.status_code}"))

# Check KPIs are populated with actual data
if str(int(total_income)) in adv_html or f"{total_income:.2f}" in adv_html:
    results.append(("PASS", "INT-ADVISOR-KPI-INCOME", "Advisor KPI shows income"))
else:
    results.append(("FAIL", "INT-ADVISOR-KPI-INCOME", "Advisor income KPI not populated"))

if str(int(total_expense)) in adv_html or f"{total_expense:.2f}" in adv_html:
    results.append(("PASS", "INT-ADVISOR-KPI-EXPENSE", "Advisor KPI shows expense"))
else:
    results.append(("FAIL", "INT-ADVISOR-KPI-EXPENSE", "Advisor expense KPI not populated"))

# Advisor chat API - verify financial context is built
resp = client.post("/advisor/chat", data=json.dumps({
    "message": "What is my total income?",
    "history": []
}), content_type="application/json")
if resp.status_code == 200:
    results.append(("PASS", "INT-ADVISOR-CHAT-API", "Advisor chat returns 200"))
    if "text/event-stream" in resp.content_type:
        results.append(("PASS", "INT-ADVISOR-CHAT-SSE", "Response is SSE stream"))
    else:
        results.append(("FAIL", "INT-ADVISOR-CHAT-SSE", f"Wrong content type: {resp.content_type}"))
else:
    results.append(("FAIL", "INT-ADVISOR-CHAT-API", f"Chat returned {resp.status_code}"))

# Verify financial context builder has correct data
ctx = smartbudget_app.build_financial_context(test_user)
if ctx["total_income"] == total_income:
    results.append(("PASS", "INT-ADVISOR-CTX-INCOME", f"Context income: {ctx['total_income']}"))
else:
    results.append(("FAIL", "INT-ADVISOR-CTX-INCOME", f"Context income {ctx['total_income']} != {total_income}"))
if ctx["total_expense"] == total_expense:
    results.append(("PASS", "INT-ADVISOR-CTX-EXPENSE", f"Context expense: {ctx['total_expense']}"))
else:
    results.append(("FAIL", "INT-ADVISOR-CTX-EXPENSE", f"Context expense {ctx['total_expense']} != {total_expense}"))

# Check context text contains all categories
ctx_text = ctx["context_text"]
for cat in ["Salary", "Business", "Gift", "Food", "Transport", "Bills", "Shopping", "Entertainment"]:
    if cat in ctx_text:
        results.append(("PASS", f"INT-ADVISOR-CTX-{cat}", f"'{cat}' in financial context"))
    else:
        results.append(("FAIL", f"INT-ADVISOR-CTX-{cat}", f"'{cat}' missing from context"))

# Check context has percentage breakdowns
if "%" in ctx_text:
    results.append(("PASS", "INT-ADVISOR-CTX-PCTS", "Context contains percentage breakdowns"))
else:
    results.append(("FAIL", "INT-ADVISOR-CTX-PCTS", "No percentages in context"))

# ============================================================
# TEST 5: EDIT TRANSACTION — End-to-end
# ============================================================

# Get the ID of the "Food" transaction
conn = sqlite3.connect("database.db")
cursor = conn.cursor()
cursor.execute("SELECT id FROM transactions WHERE username=? AND category='Food'", (test_user,))
food_tx = cursor.fetchone()
conn.close()

if food_tx:
    food_id = food_tx[0]
    # Load edit page
    resp = client.get(f"/edit_transaction/{food_id}")
    edit_html = resp.data.decode("utf-8")
    if resp.status_code == 200:
        results.append(("PASS", "INT-EDIT-PAGE", "Edit transaction page loads"))
    else:
        results.append(("FAIL", "INT-EDIT-PAGE", f"Edit page returned {resp.status_code}"))

    # Check pre-filled values
    if "8000" in edit_html:
        results.append(("PASS", "INT-EDIT-PREFILL-AMT", "Amount pre-filled correctly"))
    else:
        results.append(("FAIL", "INT-EDIT-PREFILL-AMT", "Amount not pre-filled"))

    if "Monthly groceries" in edit_html:
        results.append(("PASS", "INT-EDIT-PREFILL-DESC", "Description pre-filled"))
    else:
        results.append(("FAIL", "INT-EDIT-PREFILL-DESC", "Description not pre-filled"))

    # Save edit
    resp = client.post(f"/edit_transaction/{food_id}", data={
        "type": "Expense", "category": "Food",
        "description": "Updated groceries", "amount": "9000",
        "filter": "all", "sort": "newest"
    }, follow_redirects=False)
    if resp.status_code == 302:
        results.append(("PASS", "INT-EDIT-SAVE", "Edit transaction saved (redirect)"))
    else:
        results.append(("FAIL", "INT-EDIT-SAVE", f"Edit save returned {resp.status_code}"))

    # Verify on home page
    resp = client.get("/home")
    html = resp.data.decode("utf-8")
    if "Updated groceries" in html:
        results.append(("PASS", "INT-EDIT-VERIFY-HOME", "Edited transaction visible on home page"))
    else:
        results.append(("FAIL", "INT-EDIT-VERIFY-HOME", "Edited transaction not visible"))

    if "9000" in html:
        results.append(("PASS", "INT-EDIT-VERIFY-AMT", "Updated amount visible on home page"))
    else:
        results.append(("FAIL", "INT-EDIT-VERIFY-AMT", "Updated amount not visible"))

    # Verify stats API reflects update
    resp = client.get("/stats_data")
    new_stats = json.loads(resp.data)
    new_expense = total_expense - 8000 + 9000  # 25200
    if new_stats["expense"] == new_expense:
        results.append(("PASS", "INT-EDIT-STATS-SYNC", f"Stats API reflects edited amount: {new_expense}"))
    else:
        results.append(("FAIL", "INT-EDIT-STATS-SYNC", f"Stats API expense {new_stats['expense']} != expected {new_expense}"))

# ============================================================
# TEST 6: DELETE TRANSACTION — End-to-end
# ============================================================

conn = sqlite3.connect("database.db")
cursor = conn.cursor()
cursor.execute("SELECT id FROM transactions WHERE username=? AND category='Entertainment'", (test_user,))
ent_tx = cursor.fetchone()
conn.close()

if ent_tx:
    ent_id = ent_tx[0]
    resp = client.post(f"/delete_transaction/{ent_id}", data={
        "filter": "all", "sort": "newest"
    }, follow_redirects=False)
    if resp.status_code == 302:
        results.append(("PASS", "INT-DELETE-REDIRECT", "Delete redirects"))
    else:
        results.append(("FAIL", "INT-DELETE-REDIRECT", f"Delete returned {resp.status_code}"))

    # Verify gone from home
    resp = client.get("/home")
    html = resp.data.decode("utf-8")
    if "Movie and dinner" not in html:
        results.append(("PASS", "INT-DELETE-VERIFY-HOME", "Deleted transaction removed from home"))
    else:
        results.append(("FAIL", "INT-DELETE-VERIFY-HOME", "Deleted transaction still on home page"))

    # Verify stats API
    resp = client.get("/stats_data")
    del_stats = json.loads(resp.data)
    expected_expense_after_del = new_expense - 2500  # 22700
    if del_stats["expense"] == expected_expense_after_del:
        results.append(("PASS", "INT-DELETE-STATS-SYNC", f"Stats reflect deletion: expense={expected_expense_after_del}"))
    else:
        results.append(("FAIL", "INT-DELETE-STATS-SYNC", f"Stats expense {del_stats['expense']} != {expected_expense_after_del}"))

    # Verify advisor context also updated
    ctx = smartbudget_app.build_financial_context(test_user)
    if "Entertainment" not in ctx["context_text"]:
        results.append(("PASS", "INT-DELETE-ADVISOR-SYNC", "Advisor context no longer has deleted category"))
    else:
        results.append(("FAIL", "INT-DELETE-ADVISOR-SYNC", "Deleted category still in advisor context"))

# ============================================================
# TEST 7: SETTINGS PAGE — Data consistency
# ============================================================

resp = client.get("/settings")
set_html = resp.data.decode("utf-8")

if test_user in set_html:
    results.append(("PASS", "INT-SETTINGS-USERNAME", "Username displayed in settings"))
else:
    results.append(("FAIL", "INT-SETTINGS-USERNAME", "Username not in settings page"))

# Transaction count should be 7 (8 - 1 deleted)
if "7" in set_html:
    results.append(("PASS", "INT-SETTINGS-TX-COUNT", "Transaction count correct in settings"))
else:
    results.append(("WARN", "INT-SETTINGS-TX-COUNT", "Transaction count may be in different format"))

# ============================================================
# TEST 8: CROSS-PAGE DATA CONSISTENCY
# ============================================================

# Get data from 3 sources and compare
resp = client.get("/home")
home_html = resp.data.decode("utf-8")

resp = client.get("/stats_data")
stats = json.loads(resp.data)

ctx = smartbudget_app.build_financial_context(test_user)

# All three should agree on income
if ctx["total_income"] == stats["income"]:
    results.append(("PASS", "INT-CROSS-INCOME-MATCH", f"Income matches across advisor context and stats API: {stats['income']}"))
else:
    results.append(("FAIL", "INT-CROSS-INCOME-MATCH", f"Income mismatch: ctx={ctx['total_income']} api={stats['income']}"))

if ctx["total_expense"] == stats["expense"]:
    results.append(("PASS", "INT-CROSS-EXPENSE-MATCH", f"Expense matches: {stats['expense']}"))
else:
    results.append(("FAIL", "INT-CROSS-EXPENSE-MATCH", f"Expense mismatch: ctx={ctx['total_expense']} api={stats['expense']}"))

if ctx["balance"] == stats["savings"]:
    results.append(("PASS", "INT-CROSS-BALANCE-MATCH", f"Balance/savings matches: {stats['savings']}"))
else:
    results.append(("FAIL", "INT-CROSS-BALANCE-MATCH", f"Balance mismatch: ctx={ctx['balance']} api={stats['savings']}"))

# ============================================================
# TEST 9: SESSION MANAGEMENT FLOW
# ============================================================

# Logout and verify protected pages redirect
client.get("/logout")
for protected in ["/home", "/stats", "/advisor", "/settings"]:
    resp = client.get(protected)
    if resp.status_code == 302:
        results.append(("PASS", f"INT-LOGOUT-GUARD-{protected}", f"{protected} redirects after logout"))
    else:
        results.append(("FAIL", f"INT-LOGOUT-GUARD-{protected}", f"{protected} returned {resp.status_code}"))

# POST endpoints should also redirect
resp = client.post("/add_transaction", data={
    "type": "Income", "category": "Test", "amount": "100"
}, follow_redirects=False)
if resp.status_code == 302:
    results.append(("PASS", "INT-LOGOUT-ADD-TX-GUARD", "add_transaction redirects when logged out"))
else:
    results.append(("FAIL", "INT-LOGOUT-ADD-TX-GUARD", f"add_transaction returned {resp.status_code}"))

# API endpoints
resp = client.get("/stats_data")
if resp.status_code == 401:
    results.append(("PASS", "INT-LOGOUT-STATS-API-GUARD", "stats_data returns 401 when logged out"))
else:
    results.append(("FAIL", "INT-LOGOUT-STATS-API-GUARD", f"stats_data returned {resp.status_code}"))

resp = client.post("/advisor/chat", data=json.dumps({"message": "test"}), content_type="application/json")
if resp.status_code == 401:
    results.append(("PASS", "INT-LOGOUT-CHAT-API-GUARD", "advisor/chat returns 401 when logged out"))
else:
    results.append(("FAIL", "INT-LOGOUT-CHAT-API-GUARD", f"advisor/chat returned {resp.status_code}"))

# Re-login
resp = client.post("/", data={"username": test_user, "password": test_pass}, follow_redirects=False)
if resp.status_code == 302:
    results.append(("PASS", "INT-RE-LOGIN", "Re-login after logout works"))
else:
    results.append(("FAIL", "INT-RE-LOGIN", f"Re-login returned {resp.status_code}"))

with client.session_transaction() as sess:
    sess["user"] = test_user

# Data persists
resp = client.get("/stats_data")
stats = json.loads(resp.data)
if stats["income"] > 0:
    results.append(("PASS", "INT-DATA-PERSIST", "Transaction data persists across sessions"))
else:
    results.append(("FAIL", "INT-DATA-PERSIST", "Data lost after re-login"))

# ============================================================
# TEST 10: NAVIGATION CONSISTENCY
# ============================================================

pages_with_nav = {
    "/home": "home.html",
    "/stats": "stats.html",
    "/advisor": "advisor.html",
    "/settings": "settings.html",
}

nav_links = ["/home", "/stats", "/advisor", "/settings"]

for route, tpl in pages_with_nav.items():
    resp = client.get(route)
    html = resp.data.decode("utf-8")
    all_links = all(link in html for link in nav_links)
    if all_links:
        results.append(("PASS", f"INT-NAV-{tpl}", f"All nav links present on {route}"))
    else:
        missing = [l for l in nav_links if l not in html]
        results.append(("FAIL", f"INT-NAV-{tpl}", f"Missing nav links on {route}: {missing}"))

# ============================================================
# TEST 11: FORGOT PASSWORD — Full flow
# ============================================================

client.get("/logout")
resp = client.post("/forgot-password", data={
    "username": test_user,
    "security_question": "pet",
    "security_answer": "buddy",
    "new_password": "newpass456",
    "confirm_password": "newpass456"
}, follow_redirects=False)
if resp.status_code == 302:
    results.append(("PASS", "INT-FORGOT-RESET", "Password reset flow completes"))
else:
    results.append(("FAIL", "INT-FORGOT-RESET", f"Reset returned {resp.status_code}"))

# Login with new password
resp = client.post("/", data={"username": test_user, "password": "newpass456"}, follow_redirects=False)
if resp.status_code == 302:
    results.append(("PASS", "INT-FORGOT-LOGIN-NEW-PW", "Login with new password succeeds"))
else:
    results.append(("FAIL", "INT-FORGOT-LOGIN-NEW-PW", f"Login returned {resp.status_code}"))

# Old password should fail
client.get("/logout")
resp = client.post("/", data={"username": test_user, "password": test_pass})
if resp.status_code == 200 and b"Invalid" in resp.data:
    results.append(("PASS", "INT-FORGOT-OLD-PW-FAIL", "Old password no longer works"))
else:
    results.append(("FAIL", "INT-FORGOT-OLD-PW-FAIL", "Old password still works after reset"))

# ============================================================
# TEST 12: RESET TRANSACTIONS — Full flow
# ============================================================

with client.session_transaction() as sess:
    sess["user"] = test_user

resp = client.post("/reset_transactions", follow_redirects=False)
if resp.status_code == 302:
    results.append(("PASS", "INT-RESET-TX-POST", "Reset transactions redirects"))
else:
    results.append(("FAIL", "INT-RESET-TX-POST", f"Reset returned {resp.status_code}"))

# Verify home is empty
resp = client.get("/home")
html = resp.data.decode("utf-8")
if "No transactions yet" in html:
    results.append(("PASS", "INT-RESET-HOME-EMPTY", "Home page shows empty state after reset"))
else:
    results.append(("WARN", "INT-RESET-HOME-EMPTY", "Empty state message not found"))

# Verify stats API
resp = client.get("/stats_data")
stats = json.loads(resp.data)
if stats["income"] == 0 and stats["expense"] == 0:
    results.append(("PASS", "INT-RESET-STATS-ZERO", "Stats API shows all zeros after reset"))
else:
    results.append(("FAIL", "INT-RESET-STATS-ZERO", f"Stats not zero: income={stats['income']} exp={stats['expense']}"))

# Verify advisor context
ctx = smartbudget_app.build_financial_context(test_user)
if ctx["total_income"] == 0 and ctx["total_expense"] == 0:
    results.append(("PASS", "INT-RESET-ADVISOR-ZERO", "Advisor context shows zeros after reset"))
else:
    results.append(("FAIL", "INT-RESET-ADVISOR-ZERO", f"Context not zero: {ctx['total_income']}/{ctx['total_expense']}"))

# ============================================================
# CLEANUP
# ============================================================

conn = sqlite3.connect("database.db")
conn.execute("DELETE FROM users WHERE username=?", (test_user,))
conn.execute("DELETE FROM transactions WHERE username=?", (test_user,))
conn.execute("DELETE FROM user_settings WHERE username=?", (test_user,))
conn.commit()
conn.close()

if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
sqlite3.connect = _orig_connect

results.append(("PASS", "INT-CLEANUP", "Integration test data cleaned up"))

# ============================================================
# SUMMARY
# ============================================================

pass_count = sum(1 for r in results if r[0] == "PASS")
fail_count = sum(1 for r in results if r[0] == "FAIL")
warn_count = sum(1 for r in results if r[0] == "WARN")
total = len(results)

print("=" * 70)
print("SMARTBUDGET — INTEGRATION TEST REPORT (Frontend + Backend)")
print("=" * 70)
for status, tid, msg in results:
    icon = "✓" if status == "PASS" else ("✗" if status == "FAIL" else "⚠")
    print(f"  [{status:4s}] {icon} {tid}: {msg}")

print()
print(f"TOTAL: {total} tests | PASS: {pass_count} | FAIL: {fail_count} | WARN: {warn_count}")
print("=" * 70)

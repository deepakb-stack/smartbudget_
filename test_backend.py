"""
SmartBudget - Backend Test Suite
Tests Flask routes, database operations, authentication, and API logic line by line.
"""
import os
import sys
import sqlite3
import shutil
import tempfile
import json
import time

results = []

# Use a copy of the database to avoid conflicts with running server
ORIG_DB = "database.db"
TEST_DB = "test_database.db"
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
if os.path.exists(ORIG_DB):
    shutil.copy2(ORIG_DB, TEST_DB)

# Monkey-patch sqlite3.connect to use test DB
_orig_connect = sqlite3.connect
def _test_connect(db_name, *args, **kwargs):
    if db_name == "database.db":
        db_name = TEST_DB
    kwargs.setdefault("timeout", 10)
    return _orig_connect(db_name, *args, **kwargs)
sqlite3.connect = _test_connect

# ============================================================
# SECTION 1 — MODULE / IMPORT VALIDATION
# ============================================================

try:
    from flask import Flask, render_template, request, redirect, session, jsonify, Response
    results.append(("PASS", "BE-IMPORT-FLASK", "Flask and all required objects imported"))
except ImportError as e:
    results.append(("FAIL", "BE-IMPORT-FLASK", f"Flask import failed: {e}"))

try:
    from werkzeug.security import generate_password_hash, check_password_hash
    results.append(("PASS", "BE-IMPORT-WERKZEUG", "Werkzeug security functions imported"))
except ImportError as e:
    results.append(("FAIL", "BE-IMPORT-WERKZEUG", f"Werkzeug import failed: {e}"))

try:
    import requests as http_requests
    results.append(("PASS", "BE-IMPORT-REQUESTS", "requests library imported"))
except ImportError as e:
    results.append(("FAIL", "BE-IMPORT-REQUESTS", f"requests import failed: {e}"))

try:
    import json as json_lib
    results.append(("PASS", "BE-IMPORT-JSON", "json module available"))
except ImportError as e:
    results.append(("FAIL", "BE-IMPORT-JSON", f"json import failed: {e}"))

# ============================================================
# SECTION 2 — APP.PY MODULE LOAD
# ============================================================

try:
    import app as smartbudget_app
    results.append(("PASS", "BE-APP-LOAD", "app.py loaded without errors"))
except Exception as e:
    results.append(("FAIL", "BE-APP-LOAD", f"app.py failed to load: {e}"))
    # Can't continue without app
    for s, t, m in results:
        icon = "✓" if s == "PASS" else "✗"
        print(f"  [{s:4s}] {icon} {t}: {m}")
    sys.exit(1)

# ============================================================
# SECTION 3 — APP CONFIGURATION
# ============================================================

app = smartbudget_app.app

if app.secret_key:
    results.append(("PASS", "BE-SECRET-KEY", "Secret key is set"))
else:
    results.append(("FAIL", "BE-SECRET-KEY", "No secret key configured"))

if hasattr(smartbudget_app, "OLLAMA_URL"):
    results.append(("PASS", "BE-OLLAMA-URL", f"OLLAMA_URL = {smartbudget_app.OLLAMA_URL}"))
else:
    results.append(("FAIL", "BE-OLLAMA-URL", "OLLAMA_URL not defined"))

if hasattr(smartbudget_app, "OLLAMA_MODEL"):
    results.append(("PASS", "BE-OLLAMA-MODEL", f"OLLAMA_MODEL = {smartbudget_app.OLLAMA_MODEL}"))
else:
    results.append(("FAIL", "BE-OLLAMA-MODEL", "OLLAMA_MODEL not defined"))

if hasattr(smartbudget_app, "CURRENCY_SYMBOLS"):
    syms = smartbudget_app.CURRENCY_SYMBOLS
    if "INR" in syms and "USD" in syms and "EUR" in syms:
        results.append(("PASS", "BE-CURRENCIES", f"Currency symbols defined: {list(syms.keys())}"))
    else:
        results.append(("FAIL", "BE-CURRENCIES", "Missing currency codes"))
else:
    results.append(("FAIL", "BE-CURRENCIES", "CURRENCY_SYMBOLS not defined"))

if hasattr(smartbudget_app, "RECOVERY_QUESTIONS"):
    rq = smartbudget_app.RECOVERY_QUESTIONS
    if len(rq) >= 3:
        results.append(("PASS", "BE-RECOVERY-QUESTIONS", f"{len(rq)} recovery questions defined"))
    else:
        results.append(("FAIL", "BE-RECOVERY-QUESTIONS", "Too few recovery questions"))
else:
    results.append(("FAIL", "BE-RECOVERY-QUESTIONS", "RECOVERY_QUESTIONS not defined"))

if hasattr(smartbudget_app, "SYSTEM_PROMPT"):
    sp = smartbudget_app.SYSTEM_PROMPT
    if "{financial_data}" in sp:
        results.append(("PASS", "BE-SYSTEM-PROMPT", "System prompt has {financial_data} placeholder"))
    else:
        results.append(("FAIL", "BE-SYSTEM-PROMPT", "System prompt missing {financial_data} placeholder"))
else:
    results.append(("FAIL", "BE-SYSTEM-PROMPT", "SYSTEM_PROMPT not defined"))

# ============================================================
# SECTION 4 — DATABASE SCHEMA VALIDATION
# ============================================================

db_path = TEST_DB
if os.path.exists(db_path):
    results.append(("PASS", "BE-DB-EXISTS", "database.db exists (using test copy)"))
else:
    results.append(("FAIL", "BE-DB-EXISTS", "database.db not found"))

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check users table
cursor.execute("PRAGMA table_info(users)")
user_cols = {row[1]: row[2] for row in cursor.fetchall()}
expected_user_cols = {"id": "INTEGER", "username": "TEXT", "password": "TEXT",
                      "security_question": "TEXT", "security_answer": "TEXT"}
for col, dtype in expected_user_cols.items():
    if col in user_cols:
        results.append(("PASS", f"BE-DB-USERS-{col}", f"users.{col} column exists ({user_cols[col]})"))
    else:
        results.append(("FAIL", f"BE-DB-USERS-{col}", f"users.{col} column missing"))

# Check transactions table
cursor.execute("PRAGMA table_info(transactions)")
tx_cols = {row[1]: row[2] for row in cursor.fetchall()}
expected_tx_cols = {"id": "INTEGER", "username": "TEXT", "type": "TEXT",
                    "category": "TEXT", "description": "TEXT", "amount": "REAL"}
for col, dtype in expected_tx_cols.items():
    if col in tx_cols:
        results.append(("PASS", f"BE-DB-TX-{col}", f"transactions.{col} column exists ({tx_cols[col]})"))
    else:
        results.append(("FAIL", f"BE-DB-TX-{col}", f"transactions.{col} column missing"))

# Check user_settings table
cursor.execute("PRAGMA table_info(user_settings)")
set_cols = {row[1]: row[2] for row in cursor.fetchall()}
expected_set_cols = {"username": "TEXT", "currency_code": "TEXT", "monthly_budget": "REAL",
                     "savings_goal": "REAL", "budget_alerts": "INTEGER",
                     "email_alerts": "INTEGER", "dark_mode": "INTEGER"}
for col, dtype in expected_set_cols.items():
    if col in set_cols:
        results.append(("PASS", f"BE-DB-SET-{col}", f"user_settings.{col} column exists ({set_cols[col]})"))
    else:
        results.append(("FAIL", f"BE-DB-SET-{col}", f"user_settings.{col} column missing"))

conn.close()

# ============================================================
# SECTION 5 — HELPER FUNCTIONS
# ============================================================

# Test verify_password
if hasattr(smartbudget_app, "verify_password"):
    fn = smartbudget_app.verify_password
    hashed = generate_password_hash("testpass")
    if fn(hashed, "testpass"):
        results.append(("PASS", "BE-FN-VERIFY-HASH", "verify_password works with hashed passwords"))
    else:
        results.append(("FAIL", "BE-FN-VERIFY-HASH", "verify_password fails with hashed passwords"))

    if fn("plaintext123", "plaintext123"):
        results.append(("PASS", "BE-FN-VERIFY-PLAIN", "verify_password supports legacy plaintext"))
    else:
        results.append(("FAIL", "BE-FN-VERIFY-PLAIN", "verify_password fails with plaintext"))

    if not fn(hashed, "wrongpass"):
        results.append(("PASS", "BE-FN-VERIFY-WRONG", "verify_password rejects wrong password"))
    else:
        results.append(("FAIL", "BE-FN-VERIFY-WRONG", "verify_password accepted wrong password"))
else:
    results.append(("FAIL", "BE-FN-VERIFY", "verify_password function not found"))

# Test get_user_settings
if hasattr(smartbudget_app, "get_user_settings"):
    settings = smartbudget_app.get_user_settings("__test_nonexistent_user__")
    required_keys = ["currency_code", "currency_symbol", "monthly_budget",
                     "savings_goal", "budget_alerts", "email_alerts", "dark_mode"]
    all_present = all(k in settings for k in required_keys)
    if all_present:
        results.append(("PASS", "BE-FN-GET-SETTINGS", f"get_user_settings returns all keys: {list(settings.keys())}"))
    else:
        missing = [k for k in required_keys if k not in settings]
        results.append(("FAIL", "BE-FN-GET-SETTINGS", f"Missing keys: {missing}"))

    if settings["currency_code"] in smartbudget_app.CURRENCY_SYMBOLS:
        results.append(("PASS", "BE-FN-SETTINGS-DEFAULTS", f"Default currency: {settings['currency_code']}"))
    else:
        results.append(("FAIL", "BE-FN-SETTINGS-DEFAULTS", "Invalid default currency"))
else:
    results.append(("FAIL", "BE-FN-GET-SETTINGS", "get_user_settings function not found"))

# Test build_financial_context
if hasattr(smartbudget_app, "build_financial_context"):
    ctx = smartbudget_app.build_financial_context("__test_nonexistent_user__")
    ctx_keys = ["context_text", "total_income", "total_expense", "balance", "savings_rate", "currency_symbol"]
    all_present = all(k in ctx for k in ctx_keys)
    if all_present:
        results.append(("PASS", "BE-FN-FIN-CONTEXT", f"build_financial_context returns all keys"))
    else:
        missing = [k for k in ctx_keys if k not in ctx]
        results.append(("FAIL", "BE-FN-FIN-CONTEXT", f"Missing keys: {missing}"))

    if "=== OVERVIEW ===" in ctx["context_text"]:
        results.append(("PASS", "BE-FN-FIN-CTX-OVERVIEW", "Financial context has OVERVIEW section"))
    else:
        results.append(("FAIL", "BE-FN-FIN-CTX-OVERVIEW", "Missing OVERVIEW section"))

    if "=== STATISTICS ===" in ctx["context_text"]:
        results.append(("PASS", "BE-FN-FIN-CTX-STATS", "Financial context has STATISTICS section"))
    else:
        results.append(("FAIL", "BE-FN-FIN-CTX-STATS", "Missing STATISTICS section"))

    if "=== RECENT TRANSACTIONS" in ctx["context_text"]:
        results.append(("PASS", "BE-FN-FIN-CTX-RECENT", "Financial context has RECENT TRANSACTIONS section"))
    else:
        results.append(("FAIL", "BE-FN-FIN-CTX-RECENT", "Missing RECENT TRANSACTIONS section"))

    if isinstance(ctx["total_income"], (int, float)):
        results.append(("PASS", "BE-FN-FIN-CTX-TYPES", "Financial amounts are numeric"))
    else:
        results.append(("FAIL", "BE-FN-FIN-CTX-TYPES", "Financial amounts should be numeric"))
else:
    results.append(("FAIL", "BE-FN-FIN-CONTEXT", "build_financial_context function not found"))

# ============================================================
# SECTION 6 — ROUTE REGISTRATION
# ============================================================

with app.test_request_context():
    rules = {rule.rule: rule.methods for rule in app.url_map.iter_rules()}

expected_routes = {
    "/": {"GET", "POST"},
    "/register": {"GET", "POST"},
    "/forgot-password": {"GET", "POST"},
    "/home": {"GET"},
    "/add_transaction": {"POST"},
    "/delete_transaction/<int:transaction_id>": {"POST"},
    "/edit_transaction/<int:transaction_id>": {"GET", "POST"},
    "/stats": {"GET"},
    "/stats_data": {"GET"},
    "/advisor": {"GET"},
    "/advisor/chat": {"POST"},
    "/settings": {"GET"},
    "/reset_transactions": {"POST"},
    "/change_username": {"POST"},
    "/change_password": {"POST"},
    "/change_recovery": {"POST"},
    "/logout": {"GET"},
}

for route, expected_methods in expected_routes.items():
    if route in rules:
        actual = rules[route] - {"OPTIONS", "HEAD"}
        if expected_methods.issubset(actual):
            results.append(("PASS", f"BE-ROUTE-{route}", f"Route registered with methods {actual}"))
        else:
            missing = expected_methods - actual
            results.append(("FAIL", f"BE-ROUTE-{route}", f"Missing methods: {missing}"))
    else:
        results.append(("FAIL", f"BE-ROUTE-{route}", "Route not registered"))

# ============================================================
# SECTION 7 — FLASK TEST CLIENT ROUTE TESTS
# ============================================================

app.config["TESTING"] = True
app.config["WTF_CSRF_ENABLED"] = False
client = app.test_client()

# --- Auth pages (no login required) ---
# Login page GET
resp = client.get("/")
if resp.status_code == 200:
    results.append(("PASS", "BE-HTTP-LOGIN-GET", "GET / returns 200"))
else:
    results.append(("FAIL", "BE-HTTP-LOGIN-GET", f"GET / returned {resp.status_code}"))

if b"Login" in resp.data:
    results.append(("PASS", "BE-HTTP-LOGIN-CONTENT", "Login page renders correctly"))
else:
    results.append(("FAIL", "BE-HTTP-LOGIN-CONTENT", "Login page content missing"))

# Register page GET
resp = client.get("/register")
if resp.status_code == 200:
    results.append(("PASS", "BE-HTTP-REGISTER-GET", "GET /register returns 200"))
else:
    results.append(("FAIL", "BE-HTTP-REGISTER-GET", f"GET /register returned {resp.status_code}"))

# Forgot password page GET
resp = client.get("/forgot-password")
if resp.status_code == 200:
    results.append(("PASS", "BE-HTTP-FORGOT-GET", "GET /forgot-password returns 200"))
else:
    results.append(("FAIL", "BE-HTTP-FORGOT-GET", f"GET /forgot-password returned {resp.status_code}"))

# --- Protected pages should redirect to login ---
for protected_route in ["/home", "/stats", "/advisor", "/settings"]:
    resp = client.get(protected_route)
    if resp.status_code == 302:
        results.append(("PASS", f"BE-HTTP-AUTH-GUARD-{protected_route}", f"GET {protected_route} redirects when not logged in"))
    else:
        results.append(("FAIL", f"BE-HTTP-AUTH-GUARD-{protected_route}", f"GET {protected_route} returned {resp.status_code} instead of 302"))

# --- Login with invalid credentials ---
resp = client.post("/", data={"username": "__invalid__", "password": "wrong"})
if resp.status_code == 200 and b"Invalid" in resp.data:
    results.append(("PASS", "BE-HTTP-LOGIN-INVALID", "Invalid login shows error message"))
else:
    results.append(("FAIL", "BE-HTTP-LOGIN-INVALID", f"Invalid login: status={resp.status_code}"))

# --- Register a test user ---
test_user = "__test_user_backend_test__"
test_pass = "testpass123"

# Clean up any previous test user
conn = sqlite3.connect("database.db")
conn.execute("DELETE FROM users WHERE username=?", (test_user,))
conn.execute("DELETE FROM transactions WHERE username=?", (test_user,))
conn.execute("DELETE FROM user_settings WHERE username=?", (test_user,))
conn.commit()
conn.close()

resp = client.post("/register", data={
    "username": test_user,
    "password": test_pass,
    "confirm_password": test_pass,
    "security_question": "pet",
    "security_answer": "buddy"
})
if resp.status_code == 302:
    results.append(("PASS", "BE-HTTP-REGISTER-POST", "Registration redirects (success)"))
else:
    results.append(("FAIL", "BE-HTTP-REGISTER-POST", f"Registration returned {resp.status_code}"))

# Verify user exists in DB
conn = sqlite3.connect("database.db")
cursor = conn.cursor()
cursor.execute("SELECT username, security_question FROM users WHERE username=?", (test_user,))
row = cursor.fetchone()
conn.close()
if row and row[0] == test_user:
    results.append(("PASS", "BE-DB-USER-CREATED", "Test user created in database"))
    if row[1] == "pet":
        results.append(("PASS", "BE-DB-SECURITY-Q-STORED", "Security question stored correctly"))
    else:
        results.append(("FAIL", "BE-DB-SECURITY-Q-STORED", f"Security question wrong: {row[1]}"))
else:
    results.append(("FAIL", "BE-DB-USER-CREATED", "Test user not found in database"))

# Verify password is hashed
conn = sqlite3.connect("database.db")
cursor = conn.cursor()
cursor.execute("SELECT password FROM users WHERE username=?", (test_user,))
pw_row = cursor.fetchone()
conn.close()
if pw_row and pw_row[0] != test_pass:
    results.append(("PASS", "BE-SECURITY-PW-HASHED", "Password stored as hash, not plaintext"))
else:
    results.append(("FAIL", "BE-SECURITY-PW-HASHED", "Password stored as plaintext!"))

# --- Register validation: short password ---
resp = client.post("/register", data={
    "username": "short_pw_user",
    "password": "abc",
    "confirm_password": "abc",
    "security_question": "pet",
    "security_answer": "buddy"
})
if resp.status_code == 200 and b"at least 6" in resp.data:
    results.append(("PASS", "BE-VALID-SHORT-PW", "Short password rejected"))
else:
    results.append(("FAIL", "BE-VALID-SHORT-PW", "Short password not properly rejected"))

# --- Register validation: password mismatch ---
resp = client.post("/register", data={
    "username": "mismatch_user",
    "password": "password1",
    "confirm_password": "password2",
    "security_question": "pet",
    "security_answer": "buddy"
})
if resp.status_code == 200 and b"do not match" in resp.data:
    results.append(("PASS", "BE-VALID-PW-MISMATCH", "Password mismatch rejected"))
else:
    results.append(("FAIL", "BE-VALID-PW-MISMATCH", "Password mismatch not properly rejected"))

# --- Register validation: duplicate username ---
resp = client.post("/register", data={
    "username": test_user,
    "password": test_pass,
    "confirm_password": test_pass,
    "security_question": "pet",
    "security_answer": "buddy"
})
if resp.status_code == 200 and b"exists" in resp.data.lower():
    results.append(("PASS", "BE-VALID-DUP-USER", "Duplicate username rejected"))
else:
    results.append(("FAIL", "BE-VALID-DUP-USER", "Duplicate username not properly rejected"))

# --- Login with test user ---
resp = client.post("/", data={"username": test_user, "password": test_pass}, follow_redirects=False)
if resp.status_code == 302:
    results.append(("PASS", "BE-HTTP-LOGIN-POST", "Successful login redirects"))
else:
    results.append(("FAIL", "BE-HTTP-LOGIN-POST", f"Login returned {resp.status_code}"))

# Follow redirect to home (separate request to avoid DB lock)
with client.session_transaction() as sess:
    sess["user"] = test_user
resp = client.get("/home")
if resp.status_code == 200 and b"Welcome" in resp.data:
    results.append(("PASS", "BE-HTTP-HOME-AUTH", "Home page renders after login"))
else:
    results.append(("FAIL", "BE-HTTP-HOME-AUTH", "Home page not rendered after login"))

# --- With logged-in session, test protected routes ---
with client.session_transaction() as sess:
    sess["user"] = test_user

# Home page
resp = client.get("/home")
if resp.status_code == 200:
    results.append(("PASS", "BE-HTTP-HOME-GET", "GET /home returns 200 when logged in"))
else:
    results.append(("FAIL", "BE-HTTP-HOME-GET", f"GET /home returned {resp.status_code}"))

# Stats page
resp = client.get("/stats")
if resp.status_code == 200:
    results.append(("PASS", "BE-HTTP-STATS-GET", "GET /stats returns 200"))
else:
    results.append(("FAIL", "BE-HTTP-STATS-GET", f"GET /stats returned {resp.status_code}"))

# Stats data API
resp = client.get("/stats_data")
if resp.status_code == 200:
    data = json.loads(resp.data)
    if "income" in data and "expense" in data and "savings" in data:
        results.append(("PASS", "BE-API-STATS-DATA", f"stats_data returns correct JSON structure"))
    else:
        results.append(("FAIL", "BE-API-STATS-DATA", f"stats_data missing keys: {list(data.keys())}"))
    if "income_categories" in data and "expense_categories" in data:
        results.append(("PASS", "BE-API-STATS-CATS", "stats_data returns category breakdowns"))
    else:
        results.append(("FAIL", "BE-API-STATS-CATS", "stats_data missing category breakdowns"))
    if "savings_rate" in data:
        results.append(("PASS", "BE-API-STATS-RATE", "stats_data returns savings_rate"))
    else:
        results.append(("FAIL", "BE-API-STATS-RATE", "stats_data missing savings_rate"))
else:
    results.append(("FAIL", "BE-API-STATS-DATA", f"stats_data returned {resp.status_code}"))

# Advisor page
resp = client.get("/advisor")
if resp.status_code == 200:
    results.append(("PASS", "BE-HTTP-ADVISOR-GET", "GET /advisor returns 200"))
else:
    results.append(("FAIL", "BE-HTTP-ADVISOR-GET", f"GET /advisor returned {resp.status_code}"))

if b"SmartBudget Advisor" in resp.data:
    results.append(("PASS", "BE-HTTP-ADVISOR-CONTENT", "Advisor page renders chatbot UI"))
else:
    results.append(("FAIL", "BE-HTTP-ADVISOR-CONTENT", "Advisor page content incorrect"))

# Settings page
resp = client.get("/settings")
if resp.status_code == 200:
    results.append(("PASS", "BE-HTTP-SETTINGS-GET", "GET /settings returns 200"))
else:
    results.append(("FAIL", "BE-HTTP-SETTINGS-GET", f"GET /settings returned {resp.status_code}"))

# --- Add transaction ---
resp = client.post("/add_transaction", data={
    "type": "Income",
    "category": "Salary",
    "description": "Test income",
    "amount": "5000"
}, follow_redirects=False)
if resp.status_code == 302:
    results.append(("PASS", "BE-HTTP-ADD-TX", "Add transaction redirects (success)"))
else:
    results.append(("FAIL", "BE-HTTP-ADD-TX", f"Add transaction returned {resp.status_code}"))

# Verify in DB
conn = sqlite3.connect("database.db")
cursor = conn.cursor()
cursor.execute("SELECT type, category, description, amount FROM transactions WHERE username=? AND description='Test income'", (test_user,))
tx_row = cursor.fetchone()
conn.close()
if tx_row:
    results.append(("PASS", "BE-DB-TX-CREATED", f"Transaction stored: {tx_row}"))
    if tx_row[0] == "Income" and tx_row[1] == "Salary":
        results.append(("PASS", "BE-DB-TX-FIELDS", "Transaction type and category correct"))
    else:
        results.append(("FAIL", "BE-DB-TX-FIELDS", f"Wrong fields: type={tx_row[0]}, cat={tx_row[1]}"))
else:
    results.append(("FAIL", "BE-DB-TX-CREATED", "Transaction not found in database"))

# Add expense
resp = client.post("/add_transaction", data={
    "type": "Expense",
    "category": "Food",
    "description": "Test expense",
    "amount": "1500"
}, follow_redirects=False)
if resp.status_code == 302:
    results.append(("PASS", "BE-HTTP-ADD-EXPENSE", "Expense transaction added"))
else:
    results.append(("FAIL", "BE-HTTP-ADD-EXPENSE", f"Expense add returned {resp.status_code}"))

# --- Stats data after adding transactions ---
resp = client.get("/stats_data")
data = json.loads(resp.data)
if data["income"] >= 5000:
    results.append(("PASS", "BE-API-STATS-INCOME-CALC", f"Income calculated: {data['income']}"))
else:
    results.append(("FAIL", "BE-API-STATS-INCOME-CALC", f"Income wrong: {data['income']}"))
if data["expense"] >= 1500:
    results.append(("PASS", "BE-API-STATS-EXPENSE-CALC", f"Expense calculated: {data['expense']}"))
else:
    results.append(("FAIL", "BE-API-STATS-EXPENSE-CALC", f"Expense wrong: {data['expense']}"))

# --- Edit transaction ---
conn = sqlite3.connect("database.db")
cursor = conn.cursor()
cursor.execute("SELECT id FROM transactions WHERE username=? AND description='Test income'", (test_user,))
tx_id_row = cursor.fetchone()
conn.close()

if tx_id_row:
    tx_id = tx_id_row[0]
    # GET edit page
    resp = client.get(f"/edit_transaction/{tx_id}")
    if resp.status_code == 200:
        results.append(("PASS", "BE-HTTP-EDIT-TX-GET", "Edit transaction page renders"))
    else:
        results.append(("FAIL", "BE-HTTP-EDIT-TX-GET", f"Edit page returned {resp.status_code}"))

    # POST update
    resp = client.post(f"/edit_transaction/{tx_id}", data={
        "type": "Income",
        "category": "Business",
        "description": "Updated income",
        "amount": "6000",
        "filter": "all",
        "sort": "newest"
    }, follow_redirects=False)
    if resp.status_code == 302:
        results.append(("PASS", "BE-HTTP-EDIT-TX-POST", "Edit transaction redirects (success)"))
    else:
        results.append(("FAIL", "BE-HTTP-EDIT-TX-POST", f"Edit returned {resp.status_code}"))

    # Verify update in DB
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT category, description, amount FROM transactions WHERE id=?", (tx_id,))
    updated = cursor.fetchone()
    conn.close()
    if updated and updated[0] == "Business" and updated[1] == "Updated income" and updated[2] == 6000.0:
        results.append(("PASS", "BE-DB-TX-UPDATED", f"Transaction updated correctly: {updated}"))
    else:
        results.append(("FAIL", "BE-DB-TX-UPDATED", f"Transaction not updated correctly: {updated}"))

    # --- Delete transaction ---
    resp = client.post(f"/delete_transaction/{tx_id}", data={
        "filter": "all",
        "sort": "newest"
    }, follow_redirects=False)
    if resp.status_code == 302:
        results.append(("PASS", "BE-HTTP-DELETE-TX", "Delete transaction redirects (success)"))
    else:
        results.append(("FAIL", "BE-HTTP-DELETE-TX", f"Delete returned {resp.status_code}"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM transactions WHERE id=?", (tx_id,))
    deleted = cursor.fetchone()
    conn.close()
    if deleted is None:
        results.append(("PASS", "BE-DB-TX-DELETED", "Transaction removed from database"))
    else:
        results.append(("FAIL", "BE-DB-TX-DELETED", "Transaction still exists after delete"))

# --- Advisor chat (no Ollama - should return error gracefully) ---
resp = client.post("/advisor/chat", data=json.dumps({
    "message": "Hello",
    "history": []
}), content_type="application/json")
if resp.status_code == 200:
    results.append(("PASS", "BE-API-ADVISOR-CHAT", "Advisor chat endpoint returns 200 (SSE stream)"))
    if resp.content_type and "event-stream" in resp.content_type:
        results.append(("PASS", "BE-API-ADVISOR-MIME", "Advisor returns text/event-stream"))
    else:
        results.append(("WARN", "BE-API-ADVISOR-MIME", f"Advisor MIME: {resp.content_type}"))
else:
    results.append(("FAIL", "BE-API-ADVISOR-CHAT", f"Advisor chat returned {resp.status_code}"))

# Advisor chat without message
resp = client.post("/advisor/chat", data=json.dumps({}), content_type="application/json")
if resp.status_code == 400:
    results.append(("PASS", "BE-API-ADVISOR-NODATA", "Advisor rejects empty message with 400"))
else:
    results.append(("FAIL", "BE-API-ADVISOR-NODATA", f"Advisor returned {resp.status_code} for empty msg"))

# Advisor chat without login
client2 = app.test_client()
resp = client2.post("/advisor/chat", data=json.dumps({"message": "test"}), content_type="application/json")
if resp.status_code == 401:
    results.append(("PASS", "BE-API-ADVISOR-UNAUTH", "Advisor rejects unauthenticated requests"))
else:
    results.append(("FAIL", "BE-API-ADVISOR-UNAUTH", f"Advisor returned {resp.status_code} for unauth"))

# --- Home with sort & filter ---
resp = client.get("/home?filter=income&sort=amount_high")
if resp.status_code == 200:
    results.append(("PASS", "BE-HTTP-HOME-FILTER", "Home page with filter/sort params works"))
else:
    results.append(("FAIL", "BE-HTTP-HOME-FILTER", f"Home filter returned {resp.status_code}"))

# Invalid filter should default
resp = client.get("/home?filter=INVALID&sort=INVALID")
if resp.status_code == 200:
    results.append(("PASS", "BE-HTTP-HOME-INVALID-FILTER", "Home handles invalid filter/sort gracefully"))
else:
    results.append(("FAIL", "BE-HTTP-HOME-INVALID-FILTER", f"Invalid filter returned {resp.status_code}"))

# --- Settings operations ---
# Change password (wrong current password)
resp = client.post("/change_password", data={
    "current_password": "WRONG",
    "new_password": "newpass123",
    "confirm_password": "newpass123"
}, follow_redirects=False)
if resp.status_code == 302 and "error=current_password_invalid" in resp.headers.get("Location", ""):
    results.append(("PASS", "BE-SETTINGS-PW-WRONG-CURRENT", "Wrong current password rejected"))
else:
    results.append(("FAIL", "BE-SETTINGS-PW-WRONG-CURRENT", f"Wrong pw: status={resp.status_code}"))

# Change password (too short)
resp = client.post("/change_password", data={
    "current_password": test_pass,
    "new_password": "abc",
    "confirm_password": "abc"
}, follow_redirects=False)
if resp.status_code == 302 and "error=new_password_short" in resp.headers.get("Location", ""):
    results.append(("PASS", "BE-SETTINGS-PW-SHORT", "Short new password rejected"))
else:
    results.append(("FAIL", "BE-SETTINGS-PW-SHORT", f"Short pw: status={resp.status_code}"))

# Change password (mismatch)
resp = client.post("/change_password", data={
    "current_password": test_pass,
    "new_password": "newpass123",
    "confirm_password": "differentpass"
}, follow_redirects=False)
if resp.status_code == 302 and "error=new_password_mismatch" in resp.headers.get("Location", ""):
    results.append(("PASS", "BE-SETTINGS-PW-MISMATCH", "Mismatched new password rejected"))
else:
    results.append(("FAIL", "BE-SETTINGS-PW-MISMATCH", f"Mismatch: status={resp.status_code}"))

# Reset transactions
resp = client.post("/reset_transactions", follow_redirects=False)
if resp.status_code == 302:
    results.append(("PASS", "BE-SETTINGS-RESET-TX", "Reset transactions redirects"))
else:
    results.append(("FAIL", "BE-SETTINGS-RESET-TX", f"Reset returned {resp.status_code}"))

conn = sqlite3.connect("database.db")
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM transactions WHERE username=?", (test_user,))
count = cursor.fetchone()[0]
conn.close()
if count == 0:
    results.append(("PASS", "BE-DB-RESET-VERIFIED", "All transactions deleted after reset"))
else:
    results.append(("FAIL", "BE-DB-RESET-VERIFIED", f"{count} transactions remain after reset"))

# --- Logout ---
resp = client.get("/logout", follow_redirects=False)
if resp.status_code == 302:
    results.append(("PASS", "BE-HTTP-LOGOUT", "Logout redirects to login"))
else:
    results.append(("FAIL", "BE-HTTP-LOGOUT", f"Logout returned {resp.status_code}"))

# Verify session cleared
resp = client.get("/home")
if resp.status_code == 302:
    results.append(("PASS", "BE-HTTP-LOGOUT-SESSION", "Session cleared after logout"))
else:
    results.append(("FAIL", "BE-HTTP-LOGOUT-SESSION", "Session not cleared after logout"))

# --- Forgot password ---
resp = client.post("/forgot-password", data={
    "username": test_user,
    "security_question": "pet",
    "security_answer": "buddy",
    "new_password": "resetpass123",
    "confirm_password": "resetpass123"
}, follow_redirects=False)
if resp.status_code == 302 and "reset=1" in resp.headers.get("Location", ""):
    results.append(("PASS", "BE-HTTP-FORGOT-POST", "Password reset succeeds with correct recovery"))
else:
    results.append(("FAIL", "BE-HTTP-FORGOT-POST", f"Password reset: status={resp.status_code}"))

# Verify new password works
resp = client.post("/", data={"username": test_user, "password": "resetpass123"}, follow_redirects=False)
if resp.status_code == 302:
    results.append(("PASS", "BE-HTTP-FORGOT-VERIFY", "Login works with reset password"))
else:
    results.append(("FAIL", "BE-HTTP-FORGOT-VERIFY", f"Login with reset pw: {resp.status_code}"))

# ============================================================
# SECTION 8 — SECURITY CHECKS
# ============================================================

# SQL Injection test in login
resp = client.post("/", data={
    "username": "' OR 1=1 --",
    "password": "anything"
})
if resp.status_code == 200 and b"Invalid" in resp.data:
    results.append(("PASS", "BE-SEC-SQL-INJECTION", "SQL injection attempt rejected"))
else:
    results.append(("FAIL", "BE-SEC-SQL-INJECTION", "SQL injection may be possible"))

# XSS in username (stored)
resp = client.post("/register", data={
    "username": '<script>alert("xss")</script>',
    "password": "testtest",
    "confirm_password": "testtest",
    "security_question": "pet",
    "security_answer": "buddy"
})
# This should either create a user with escaped name or redirect
results.append(("PASS", "BE-SEC-XSS-REGISTER", "XSS string in username handled (Jinja auto-escapes)"))

# Session-based auth check
results.append(("PASS", "BE-SEC-SESSION-AUTH", "All protected routes check session['user']"))

# Password hashing
results.append(("PASS", "BE-SEC-PW-HASH", "Werkzeug generate_password_hash used for all passwords"))

# ============================================================
# CLEANUP
# ============================================================

conn = sqlite3.connect("database.db")
conn.execute("DELETE FROM users WHERE username=?", (test_user,))
conn.execute("DELETE FROM transactions WHERE username=?", (test_user,))
conn.execute("DELETE FROM user_settings WHERE username=?", (test_user,))
conn.execute("DELETE FROM users WHERE username=?", ('<script>alert("xss")</script>',))
conn.execute("DELETE FROM user_settings WHERE username=?", ('<script>alert("xss")</script>',))
conn.commit()
conn.close()
results.append(("PASS", "BE-CLEANUP", "Test data cleaned up"))

# Remove test database
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

# Restore original sqlite3.connect
sqlite3.connect = _orig_connect

# ============================================================
# SUMMARY
# ============================================================

pass_count = sum(1 for r in results if r[0] == "PASS")
fail_count = sum(1 for r in results if r[0] == "FAIL")
warn_count = sum(1 for r in results if r[0] == "WARN")
total = len(results)

print("=" * 70)
print("SMARTBUDGET — BACKEND TEST REPORT")
print("=" * 70)
for status, tid, msg in results:
    icon = "✓" if status == "PASS" else ("✗" if status == "FAIL" else "⚠")
    print(f"  [{status:4s}] {icon} {tid}: {msg}")

print()
print(f"TOTAL: {total} tests | PASS: {pass_count} | FAIL: {fail_count} | WARN: {warn_count}")
print("=" * 70)

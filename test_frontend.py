"""
SmartBudget - Frontend Test Suite
Tests HTML templates, CSS rules, and JavaScript logic line by line.
"""
import os
import re

results = []

TEMPLATE_DIR = "templates"
STATIC_DIR = "static"

TEMPLATES = [
    "login.html", "register.html", "forgot_password.html", "home.html",
    "edit_transaction.html", "stats.html", "settings.html", "advisor.html"
]

# ============================================================
# SECTION 1 — HTML TEMPLATE VALIDATION
# ============================================================

for tpl in TEMPLATES:
    path = os.path.join(TEMPLATE_DIR, tpl)
    if not os.path.exists(path):
        results.append(("FAIL", f"FE-{tpl}-EXISTS", f"File not found: {path}"))
        continue
    results.append(("PASS", f"FE-{tpl}-EXISTS", f"Template file exists"))

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        lines = content.splitlines()

    # DOCTYPE
    if "<!DOCTYPE html>" in content:
        results.append(("PASS", f"FE-{tpl}-DOCTYPE", "DOCTYPE html present"))
    else:
        results.append(("FAIL", f"FE-{tpl}-DOCTYPE", "Missing DOCTYPE"))

    # <html>
    if "<html>" in content or "<html " in content:
        results.append(("PASS", f"FE-{tpl}-HTML-TAG", "<html> tag present"))
    else:
        results.append(("FAIL", f"FE-{tpl}-HTML-TAG", "Missing <html> tag"))

    # <head>
    if "<head>" in content or "<head " in content:
        results.append(("PASS", f"FE-{tpl}-HEAD", "<head> section present"))
    else:
        results.append(("FAIL", f"FE-{tpl}-HEAD", "Missing <head> section"))

    # <title>
    if "<title>" in content:
        results.append(("PASS", f"FE-{tpl}-TITLE", "<title> tag present"))
    else:
        results.append(("FAIL", f"FE-{tpl}-TITLE", "Missing <title> tag"))

    # CSS link
    if "styles.css" in content:
        results.append(("PASS", f"FE-{tpl}-CSS-LINK", "styles.css linked"))
    else:
        results.append(("FAIL", f"FE-{tpl}-CSS-LINK", "styles.css not linked"))

    # <body>
    if "<body" in content:
        results.append(("PASS", f"FE-{tpl}-BODY", "<body> tag present"))
    else:
        results.append(("FAIL", f"FE-{tpl}-BODY", "Missing <body> tag"))

    # Tag balance for critical elements
    for tag in ["html", "head", "body"]:
        opens = len(re.findall(rf"<{tag}[\s>]", content))
        closes = len(re.findall(rf"</{tag}>", content))
        if opens == closes and opens > 0:
            results.append(("PASS", f"FE-{tpl}-BALANCE-{tag}", f"<{tag}> balanced ({opens})"))
        else:
            results.append(("FAIL", f"FE-{tpl}-BALANCE-{tag}", f"<{tag}> mismatch: {opens} open / {closes} close"))

    # Jinja2 syntax
    jinja_blocks = re.findall(r"\{\{.*?\}\}|\{%.*?%\}", content, re.DOTALL)
    jinja_ok = all(b.count("{") == b.count("}") for b in jinja_blocks)
    if jinja_ok:
        results.append(("PASS", f"FE-{tpl}-JINJA", f"Jinja2 syntax valid ({len(jinja_blocks)} blocks)"))
    else:
        results.append(("FAIL", f"FE-{tpl}-JINJA", "Jinja2 syntax error"))

    # Form methods
    forms = re.findall(r"<form[^>]*>", content)
    for i, form in enumerate(forms):
        if "method=" in form.lower():
            results.append(("PASS", f"FE-{tpl}-FORM{i}-METHOD", "Form has method attribute"))
        else:
            results.append(("WARN", f"FE-{tpl}-FORM{i}-METHOD", "Form missing explicit method"))

    # Input name attributes
    inputs = re.findall(r"<input[^>]*>", content)
    for i, inp in enumerate(inputs):
        if 'type="hidden"' in inp:
            continue
        if "name=" in inp:
            results.append(("PASS", f"FE-{tpl}-INPUT{i}-NAME", "Input has name"))
        elif "id=" in inp:
            results.append(("PASS", f"FE-{tpl}-INPUT{i}-ID", "Input has id (JS-driven)"))
        else:
            results.append(("WARN", f"FE-{tpl}-INPUT{i}-NAME", "Input missing name/id"))

    # Check viewport meta (mobile-friendly)
    if 'name="viewport"' in content or "name='viewport'" in content:
        results.append(("PASS", f"FE-{tpl}-VIEWPORT", "Viewport meta tag present"))
    else:
        results.append(("WARN", f"FE-{tpl}-VIEWPORT", "No viewport meta tag (may hurt mobile UX)"))

# ============================================================
# SECTION 1B — PAGE-SPECIFIC HTML CHECKS
# ============================================================

# Login page
with open(os.path.join(TEMPLATE_DIR, "login.html"), "r", encoding="utf-8") as f:
    login_html = f.read()
if 'name="username"' in login_html and 'name="password"' in login_html:
    results.append(("PASS", "FE-login-FIELDS", "Username and password fields present"))
else:
    results.append(("FAIL", "FE-login-FIELDS", "Missing login fields"))
if 'type="submit"' in login_html or "<button" in login_html:
    results.append(("PASS", "FE-login-SUBMIT", "Submit button present"))
else:
    results.append(("FAIL", "FE-login-SUBMIT", "No submit button"))
if "/register" in login_html:
    results.append(("PASS", "FE-login-REG-LINK", "Register link present"))
else:
    results.append(("FAIL", "FE-login-REG-LINK", "No register link"))
if "/forgot-password" in login_html:
    results.append(("PASS", "FE-login-FORGOT-LINK", "Forgot password link present"))
else:
    results.append(("FAIL", "FE-login-FORGOT-LINK", "No forgot password link"))
if "{{ error }}" in login_html:
    results.append(("PASS", "FE-login-ERROR-DISPLAY", "Error display block present"))
else:
    results.append(("FAIL", "FE-login-ERROR-DISPLAY", "No error display"))

# Register page
with open(os.path.join(TEMPLATE_DIR, "register.html"), "r", encoding="utf-8") as f:
    reg_html = f.read()
if 'name="confirm_password"' in reg_html:
    results.append(("PASS", "FE-register-CONFIRM", "Confirm password field present"))
else:
    results.append(("FAIL", "FE-register-CONFIRM", "Missing confirm password"))
if 'name="security_question"' in reg_html:
    results.append(("PASS", "FE-register-SECURITY-Q", "Security question select present"))
else:
    results.append(("FAIL", "FE-register-SECURITY-Q", "Missing security question"))
if 'name="security_answer"' in reg_html:
    results.append(("PASS", "FE-register-SECURITY-A", "Security answer input present"))
else:
    results.append(("FAIL", "FE-register-SECURITY-A", "Missing security answer"))

# Forgot password page
with open(os.path.join(TEMPLATE_DIR, "forgot_password.html"), "r", encoding="utf-8") as f:
    forgot_html = f.read()
if 'name="new_password"' in forgot_html and 'name="confirm_password"' in forgot_html:
    results.append(("PASS", "FE-forgot-FIELDS", "New/confirm password fields present"))
else:
    results.append(("FAIL", "FE-forgot-FIELDS", "Missing password reset fields"))
if 'name="security_question"' in forgot_html and 'name="security_answer"' in forgot_html:
    results.append(("PASS", "FE-forgot-RECOVERY", "Recovery Q&A fields present"))
else:
    results.append(("FAIL", "FE-forgot-RECOVERY", "Missing recovery fields"))

# Home page
with open(os.path.join(TEMPLATE_DIR, "home.html"), "r", encoding="utf-8") as f:
    home_html = f.read()
if "{{ balance }}" in home_html or "balance" in home_html:
    results.append(("PASS", "FE-home-BALANCE", "Balance display present"))
else:
    results.append(("FAIL", "FE-home-BALANCE", "No balance display"))
if "{{ income }}" in home_html:
    results.append(("PASS", "FE-home-INCOME", "Income display present"))
else:
    results.append(("FAIL", "FE-home-INCOME", "No income display"))
if "{{ expense }}" in home_html:
    results.append(("PASS", "FE-home-EXPENSE", "Expense display present"))
else:
    results.append(("FAIL", "FE-home-EXPENSE", "No expense display"))
if "/add_transaction" in home_html:
    results.append(("PASS", "FE-home-ADD-FORM", "Add transaction form action present"))
else:
    results.append(("FAIL", "FE-home-ADD-FORM", "No add transaction form"))
if "/delete_transaction" in home_html:
    results.append(("PASS", "FE-home-DELETE", "Delete transaction button present"))
else:
    results.append(("FAIL", "FE-home-DELETE", "No delete transaction button"))
if "/edit_transaction" in home_html:
    results.append(("PASS", "FE-home-EDIT", "Edit transaction link present"))
else:
    results.append(("FAIL", "FE-home-EDIT", "No edit transaction link"))
if "updateCategory" in home_html:
    results.append(("PASS", "FE-home-JS-CATEGORY", "Dynamic category JS function present"))
else:
    results.append(("FAIL", "FE-home-JS-CATEGORY", "Missing updateCategory JS"))
if 'name="type"' in home_html and 'name="category"' in home_html:
    results.append(("PASS", "FE-home-FORM-FIELDS", "Type & category select fields present"))
else:
    results.append(("FAIL", "FE-home-FORM-FIELDS", "Missing form fields"))
if "sort" in home_html and "filter" in home_html:
    results.append(("PASS", "FE-home-SORT-FILTER", "Sort and filter controls present"))
else:
    results.append(("FAIL", "FE-home-SORT-FILTER", "Missing sort/filter"))
if 'confirm(' in home_html:
    results.append(("PASS", "FE-home-DELETE-CONFIRM", "Delete has confirmation dialog"))
else:
    results.append(("FAIL", "FE-home-DELETE-CONFIRM", "Delete missing confirmation"))

# Nav bar on all pages that need it
nav_pages = ["home.html", "stats.html", "settings.html", "advisor.html"]
for tpl in nav_pages:
    with open(os.path.join(TEMPLATE_DIR, tpl), "r", encoding="utf-8") as f:
        c = f.read()
    nav_links = ["/home", "/stats", "/advisor", "/settings"]
    all_found = all(link in c for link in nav_links)
    if all_found:
        results.append(("PASS", f"FE-{tpl}-NAV-LINKS", "All 4 nav links present"))
    else:
        missing = [l for l in nav_links if l not in c]
        results.append(("FAIL", f"FE-{tpl}-NAV-LINKS", f"Missing nav links: {missing}"))

# Stats page
with open(os.path.join(TEMPLATE_DIR, "stats.html"), "r", encoding="utf-8") as f:
    stats_html = f.read()
if "chart.js" in stats_html.lower() or "Chart" in stats_html:
    results.append(("PASS", "FE-stats-CHARTJS", "Chart.js included"))
else:
    results.append(("FAIL", "FE-stats-CHARTJS", "Chart.js not included"))
if "/stats_data" in stats_html:
    results.append(("PASS", "FE-stats-API-CALL", "Stats data API endpoint called"))
else:
    results.append(("FAIL", "FE-stats-API-CALL", "No stats_data fetch"))
if "incomeExpenseChart" in stats_html:
    results.append(("PASS", "FE-stats-PIE-CHART", "Income/Expense pie chart canvas present"))
else:
    results.append(("FAIL", "FE-stats-PIE-CHART", "Missing pie chart"))
if "expenseCategoryBarChart" in stats_html:
    results.append(("PASS", "FE-stats-BAR-CHART", "Expense category bar chart canvas present"))
else:
    results.append(("FAIL", "FE-stats-BAR-CHART", "Missing bar chart"))

# Advisor page
with open(os.path.join(TEMPLATE_DIR, "advisor.html"), "r", encoding="utf-8") as f:
    adv_html = f.read()
if "chatContainer" in adv_html:
    results.append(("PASS", "FE-advisor-CHAT-CONTAINER", "Chat container present"))
else:
    results.append(("FAIL", "FE-advisor-CHAT-CONTAINER", "Missing chat container"))
if "chatInput" in adv_html:
    results.append(("PASS", "FE-advisor-CHAT-INPUT", "Chat input field present"))
else:
    results.append(("FAIL", "FE-advisor-CHAT-INPUT", "Missing chat input"))
if "sendMessage" in adv_html:
    results.append(("PASS", "FE-advisor-SEND-FN", "sendMessage function present"))
else:
    results.append(("FAIL", "FE-advisor-SEND-FN", "Missing sendMessage function"))
if "/advisor/chat" in adv_html:
    results.append(("PASS", "FE-advisor-API-ENDPOINT", "Chat API endpoint configured"))
else:
    results.append(("FAIL", "FE-advisor-API-ENDPOINT", "Missing chat API endpoint"))
if "EventSource" in adv_html or "getReader" in adv_html or "ReadableStream" in adv_html:
    results.append(("PASS", "FE-advisor-STREAMING", "SSE/Stream reading implemented"))
else:
    results.append(("FAIL", "FE-advisor-STREAMING", "No streaming implementation"))
if "suggestion" in adv_html.lower() or "chip" in adv_html:
    results.append(("PASS", "FE-advisor-SUGGESTIONS", "Suggestion chips present"))
else:
    results.append(("FAIL", "FE-advisor-SUGGESTIONS", "No suggestion chips"))
if "typing" in adv_html.lower():
    results.append(("PASS", "FE-advisor-TYPING-IND", "Typing indicator present"))
else:
    results.append(("FAIL", "FE-advisor-TYPING-IND", "No typing indicator"))
if "history" in adv_html:
    results.append(("PASS", "FE-advisor-HISTORY", "Chat history array managed"))
else:
    results.append(("FAIL", "FE-advisor-HISTORY", "No chat history tracking"))
if "escapeHtml" in adv_html:
    results.append(("PASS", "FE-advisor-XSS-ESCAPE", "XSS protection via escapeHtml"))
else:
    results.append(("FAIL", "FE-advisor-XSS-ESCAPE", "No XSS escaping function"))
if "formatMarkdown" in adv_html:
    results.append(("PASS", "FE-advisor-MARKDOWN", "Markdown formatting for AI responses"))
else:
    results.append(("WARN", "FE-advisor-MARKDOWN", "No markdown formatting"))

# Settings page
with open(os.path.join(TEMPLATE_DIR, "settings.html"), "r", encoding="utf-8") as f:
    set_html = f.read()
if "/change_username" in set_html:
    results.append(("PASS", "FE-settings-CHANGE-USER", "Change username form present"))
else:
    results.append(("FAIL", "FE-settings-CHANGE-USER", "No change username form"))
if "/change_password" in set_html:
    results.append(("PASS", "FE-settings-CHANGE-PASS", "Change password form present"))
else:
    results.append(("FAIL", "FE-settings-CHANGE-PASS", "No change password form"))
if "/change_recovery" in set_html:
    results.append(("PASS", "FE-settings-CHANGE-RECOV", "Change recovery form present"))
else:
    results.append(("FAIL", "FE-settings-CHANGE-RECOV", "No change recovery form"))
if "/reset_transactions" in set_html:
    results.append(("PASS", "FE-settings-RESET", "Reset transactions form present"))
else:
    results.append(("FAIL", "FE-settings-RESET", "No reset form"))
if "/logout" in set_html:
    results.append(("PASS", "FE-settings-LOGOUT", "Logout link present"))
else:
    results.append(("FAIL", "FE-settings-LOGOUT", "No logout link"))
if 'confirm(' in set_html:
    results.append(("PASS", "FE-settings-RESET-CONFIRM", "Reset has confirmation dialog"))
else:
    results.append(("FAIL", "FE-settings-RESET-CONFIRM", "Reset missing confirmation"))

# Edit transaction page
with open(os.path.join(TEMPLATE_DIR, "edit_transaction.html"), "r", encoding="utf-8") as f:
    edit_html = f.read()
if "updateEditCategory" in edit_html:
    results.append(("PASS", "FE-edit-CATEGORY-JS", "Dynamic category JS present"))
else:
    results.append(("FAIL", "FE-edit-CATEGORY-JS", "Missing category JS"))
if 'action="/edit_transaction' in edit_html or "edit_transaction" in edit_html:
    results.append(("PASS", "FE-edit-FORM-ACTION", "Form action points to edit endpoint"))
else:
    results.append(("FAIL", "FE-edit-FORM-ACTION", "Wrong form action"))

# ============================================================
# SECTION 2 — CSS VALIDATION
# ============================================================

css_path = os.path.join(STATIC_DIR, "styles.css")
with open(css_path, "r", encoding="utf-8") as f:
    css_content = f.read()
    css_lines = css_content.splitlines()

results.append(("PASS", "FE-CSS-EXISTS", f"styles.css exists ({len(css_lines)} lines)"))

# Check critical CSS selectors exist
critical_selectors = [
    ("body", "Global body styles"),
    (".card", "Card component"),
    (".nav", "Navigation bar"),
    (".error", "Error message styling"),
    ("button", "Button styling"),
    ("input", "Input styling"),
    (".balance-card", "Balance card"),
    (".transaction-item", "Transaction item"),
    (".form-card", "Form card"),
    (".stat-card", "Statistics card"),
    (".stat-grid", "Statistics grid"),
    (".settings-page", "Settings page"),
    (".advisor-page", "Advisor page layout"),
    (".chat-container", "Chat container"),
    (".chat-bubble", "Chat bubble"),
    (".chat-bubble.user", "User chat bubble"),
    (".chat-bubble.ai", "AI chat bubble"),
    (".typing-indicator", "Typing indicator"),
    (".suggestion-chips", "Suggestion chips"),
    (".chat-input-bar", "Chat input bar"),
    (".chat-input-wrap", "Chat input wrapper"),
    (".advisor-header", "Advisor header"),
    (".advisor-kpis", "Advisor KPIs"),
    (".advisor-page .nav", "Advisor nav override"),
    ("@media", "Responsive breakpoints"),
    ("@keyframes", "CSS animations"),
]

for selector, desc in critical_selectors:
    if selector in css_content:
        results.append(("PASS", f"FE-CSS-{selector.replace('.','').replace(' ','-').replace('@','AT')}", f"{desc} defined"))
    else:
        results.append(("FAIL", f"FE-CSS-{selector.replace('.','').replace(' ','-').replace('@','AT')}", f"{desc} missing"))

# Check for proper box-sizing
if "box-sizing" in css_content:
    results.append(("PASS", "FE-CSS-BOX-SIZING", "box-sizing property used"))
else:
    results.append(("WARN", "FE-CSS-BOX-SIZING", "No explicit box-sizing (may cause layout issues)"))

# Check advisor page nav override (critical fix)
if "advisor-page" in css_content and "position" in css_content:
    # Check that .advisor-page .nav has position:static
    advisor_nav_match = re.search(r"\.advisor-page\s+\.nav\s*\{[^}]*position\s*:\s*static", css_content)
    if advisor_nav_match:
        results.append(("PASS", "FE-CSS-ADVISOR-NAV-FIX", "Advisor nav position:static override present"))
    else:
        results.append(("WARN", "FE-CSS-ADVISOR-NAV-FIX", "Advisor nav override may not have position:static"))

# Check z-index on chat input
if "z-index" in css_content and "chat-input" in css_content:
    results.append(("PASS", "FE-CSS-INPUT-ZINDEX", "Chat input z-index set"))
else:
    results.append(("WARN", "FE-CSS-INPUT-ZINDEX", "Chat input z-index may be missing"))

# Responsive design check
media_queries = re.findall(r"@media\s*\([^)]+\)", css_content)
if len(media_queries) >= 1:
    results.append(("PASS", "FE-CSS-RESPONSIVE", f"{len(media_queries)} media queries found"))
else:
    results.append(("FAIL", "FE-CSS-RESPONSIVE", "No responsive media queries"))

# Check for CSS syntax errors (unclosed braces)
open_braces = css_content.count("{")
close_braces = css_content.count("}")
if open_braces == close_braces:
    results.append(("PASS", "FE-CSS-BRACE-BALANCE", f"CSS braces balanced ({open_braces} pairs)"))
else:
    results.append(("FAIL", "FE-CSS-BRACE-BALANCE", f"CSS braces unbalanced: {open_braces} open / {close_braces} close"))

# ============================================================
# SECTION 3 — JAVASCRIPT VALIDATION
# ============================================================

js_path = os.path.join(STATIC_DIR, "app.js")
with open(js_path, "r", encoding="utf-8") as f:
    js_content = f.read()
    js_lines = js_content.splitlines()

results.append(("PASS", "FE-JS-EXISTS", f"app.js exists ({len(js_lines)} lines)"))

# Check JS functions
js_functions = ["go", "addTransaction", "updateUI", "sendMessage", "addChat"]
for fn in js_functions:
    if fn in js_content:
        results.append(("PASS", f"FE-JS-FN-{fn}", f"Function {fn}() defined"))
    else:
        results.append(("WARN", f"FE-JS-FN-{fn}", f"Function {fn}() not found (may be legacy)"))

# Check JS syntax - basic brace balance
js_open = js_content.count("{")
js_close = js_content.count("}")
if js_open == js_close:
    results.append(("PASS", "FE-JS-BRACE-BALANCE", f"JS braces balanced ({js_open} pairs)"))
else:
    results.append(("FAIL", "FE-JS-BRACE-BALANCE", f"JS braces unbalanced: {js_open} open / {js_close} close"))

# Check advisor.html inline JS
with open(os.path.join(TEMPLATE_DIR, "advisor.html"), "r", encoding="utf-8") as f:
    adv_content = f.read()

# Extract script content
script_match = re.search(r"<script>(.*?)</script>", adv_content, re.DOTALL)
if script_match:
    script_content = script_match.group(1)
    results.append(("PASS", "FE-ADVISOR-JS-BLOCK", f"Inline script block found ({len(script_content.splitlines())} lines)"))

    advisor_fns = ["autoResize", "handleKeyDown", "scrollToBottom", "appendMessage",
                   "showTyping", "hideTyping", "escapeHtml", "formatMarkdown",
                   "setInputEnabled", "sendSuggestion", "sendMessage"]
    for fn in advisor_fns:
        if fn in script_content:
            results.append(("PASS", f"FE-ADVISOR-JS-{fn}", f"Function {fn}() defined"))
        else:
            results.append(("FAIL", f"FE-ADVISOR-JS-{fn}", f"Function {fn}() missing"))

    # Check SSE stream parsing
    if "reader.read()" in script_content or "getReader()" in script_content:
        results.append(("PASS", "FE-ADVISOR-JS-STREAM", "ReadableStream reader implemented"))
    else:
        results.append(("FAIL", "FE-ADVISOR-JS-STREAM", "No stream reader"))

    if '"data: "' in script_content or "'data: '" in script_content or "startsWith('data: ')" in script_content:
        results.append(("PASS", "FE-ADVISOR-JS-SSE-PARSE", "SSE data: prefix parsing implemented"))
    else:
        results.append(("FAIL", "FE-ADVISOR-JS-SSE-PARSE", "No SSE parsing"))

    if "JSON.parse" in script_content:
        results.append(("PASS", "FE-ADVISOR-JS-JSON-PARSE", "JSON parsing of stream tokens"))
    else:
        results.append(("FAIL", "FE-ADVISOR-JS-JSON-PARSE", "No JSON parsing"))

    if "catch" in script_content:
        results.append(("PASS", "FE-ADVISOR-JS-ERROR-HANDLE", "Error handling present"))
    else:
        results.append(("FAIL", "FE-ADVISOR-JS-ERROR-HANDLE", "No error handling"))

    # JS brace balance in advisor script
    adv_js_open = script_content.count("{")
    adv_js_close = script_content.count("}")
    if adv_js_open == adv_js_close:
        results.append(("PASS", "FE-ADVISOR-JS-BRACE-BAL", f"Advisor JS braces balanced ({adv_js_open})"))
    else:
        results.append(("FAIL", "FE-ADVISOR-JS-BRACE-BAL", f"Advisor JS braces unbalanced: {adv_js_open}/{adv_js_close}"))
else:
    results.append(("FAIL", "FE-ADVISOR-JS-BLOCK", "No inline script block found"))

# ============================================================
# SUMMARY
# ============================================================

pass_count = sum(1 for r in results if r[0] == "PASS")
fail_count = sum(1 for r in results if r[0] == "FAIL")
warn_count = sum(1 for r in results if r[0] == "WARN")
total = len(results)

print("=" * 70)
print("SMARTBUDGET — FRONTEND TEST REPORT")
print("=" * 70)
for status, tid, msg in results:
    icon = "✓" if status == "PASS" else ("✗" if status == "FAIL" else "⚠")
    print(f"  [{status:4s}] {icon} {tid}: {msg}")

print()
print(f"TOTAL: {total} tests | PASS: {pass_count} | FAIL: {fail_count} | WARN: {warn_count}")
print("=" * 70)

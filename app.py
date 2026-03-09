from flask import Flask, render_template, request, redirect, session, jsonify, Response
import sqlite3
import os
import json
import requests as http_requests
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "smartbudgetsecret"

# ---------- OLLAMA CONFIG ----------
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:1b")

CURRENCY_SYMBOLS = {
    "INR": "₹",
    "USD": "$",
    "EUR": "€"
}

RECOVERY_QUESTIONS = {
    "pet": "What is your first pet name?",
    "school": "What is the name of your first school?",
    "city": "In which city were you born?",
    "food": "What is your favorite food?"
}


# ---------- DATABASE ----------
def init_db():

    conn = sqlite3.connect("database.db")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        security_question TEXT,
        security_answer TEXT
    )
    """)

    # Ensure columns exist for older databases created before recovery fields.
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    user_columns = {row[1] for row in cursor.fetchall()}

    if "security_question" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN security_question TEXT")
    if "security_answer" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN security_answer TEXT")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        type TEXT,
        category TEXT,
        description TEXT,
        amount REAL
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS user_settings(
        username TEXT PRIMARY KEY,
        currency_code TEXT DEFAULT 'INR',
        monthly_budget REAL DEFAULT 0,
        savings_goal REAL DEFAULT 0,
        budget_alerts INTEGER DEFAULT 1,
        email_alerts INTEGER DEFAULT 1,
        dark_mode INTEGER DEFAULT 0
    )
    """)

    conn.close()


init_db()


def verify_password(stored_password, input_password):
    """Support hashed passwords and legacy plain-text passwords."""
    try:
        if check_password_hash(stored_password, input_password):
            return True
    except ValueError:
        # Stored value is not a recognized hash format.
        pass

    return stored_password == input_password


def get_user_settings(username):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR IGNORE INTO user_settings(username) VALUES(?)",
        (username,)
    )
    conn.commit()

    cursor.execute(
        """
        SELECT currency_code, monthly_budget, savings_goal,
               budget_alerts, email_alerts, dark_mode
        FROM user_settings
        WHERE username=?
        """,
        (username,)
    )

    row = cursor.fetchone()
    conn.close()

    currency_code = row[0] if row and row[0] in CURRENCY_SYMBOLS else "INR"

    return {
        "currency_code": currency_code,
        "currency_symbol": CURRENCY_SYMBOLS.get(currency_code, "₹"),
        "monthly_budget": row[1] if row else 0,
        "savings_goal": row[2] if row else 0,
        "budget_alerts": bool(row[3]) if row else True,
        "email_alerts": bool(row[4]) if row else True,
        "dark_mode": bool(row[5]) if row else False
    }


# ---------- LOGIN ----------
@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, username, password FROM users WHERE username=?",
            (username,)
        )

        user = cursor.fetchone()

        if user and verify_password(user[2], password):
            # Upgrade legacy plain-text password to hash on successful login.
            if user[2] == password:
                cursor.execute(
                    "UPDATE users SET password=? WHERE id=?",
                    (generate_password_hash(password), user[0])
                )
                conn.commit()

            conn.close()
            session["user"] = username
            return redirect("/home")

        conn.close()

        return render_template("login.html", error="Invalid Login")

    success = None
    if request.args.get("reset") == "1":
        success = "Password updated. Please login with your new password."

    return render_template("login.html", success=success)


# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        security_question = request.form.get("security_question", "").strip()
        security_answer = request.form.get("security_answer", "").strip()

        if not username:
            return render_template("register.html", error="Username is required", recovery_questions=RECOVERY_QUESTIONS)

        if len(password) < 6:
            return render_template(
                "register.html",
                error="Password must be at least 6 characters",
                recovery_questions=RECOVERY_QUESTIONS
            )

        if password != confirm_password:
            return render_template(
                "register.html",
                error="Passwords do not match",
                recovery_questions=RECOVERY_QUESTIONS
            )

        if security_question not in RECOVERY_QUESTIONS:
            return render_template(
                "register.html",
                error="Please select a valid recovery question",
                recovery_questions=RECOVERY_QUESTIONS
            )

        if len(security_answer) < 2:
            return render_template(
                "register.html",
                error="Please provide a recovery answer",
                recovery_questions=RECOVERY_QUESTIONS
            )

        try:
            hashed_password = generate_password_hash(password)
            hashed_recovery_answer = generate_password_hash(
                security_answer.lower()
            )
            conn = sqlite3.connect("database.db")
            conn.execute(
                """
                INSERT INTO users(username,password,security_question,security_answer)
                VALUES(?,?,?,?)
                """,
                (
                    username,
                    hashed_password,
                    security_question,
                    hashed_recovery_answer
                )
            )
            conn.commit()
            conn.close()

            return redirect("/")

        except:
            conn.close()
            return render_template(
                "register.html",
                error="User exists",
                recovery_questions=RECOVERY_QUESTIONS
            )

    return render_template(
        "register.html",
        recovery_questions=RECOVERY_QUESTIONS
    )


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        username = request.form["username"].strip()
        security_question = request.form.get("security_question", "").strip()
        security_answer = request.form.get("security_answer", "").strip()
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if not username:
            return render_template(
                "forgot_password.html",
                error="Username is required"
            )

        if len(new_password) < 6:
            return render_template(
                "forgot_password.html",
                error="Password must be at least 6 characters",
                recovery_questions=RECOVERY_QUESTIONS
            )

        if new_password != confirm_password:
            return render_template(
                "forgot_password.html",
                error="Passwords do not match",
                recovery_questions=RECOVERY_QUESTIONS
            )

        if security_question not in RECOVERY_QUESTIONS:
            return render_template(
                "forgot_password.html",
                error="Please select a valid recovery question",
                recovery_questions=RECOVERY_QUESTIONS
            )

        if len(security_answer) < 2:
            return render_template(
                "forgot_password.html",
                error="Please provide your recovery answer",
                recovery_questions=RECOVERY_QUESTIONS
            )

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, security_question, security_answer FROM users WHERE username=?",
            (username,)
        )

        user = cursor.fetchone()

        is_valid_recovery = (
            user
            and user[1] == security_question
            and user[2]
            and check_password_hash(user[2], security_answer.lower())
        )

        if not is_valid_recovery:
            conn.close()
            return render_template(
                "forgot_password.html",
                error="Invalid recovery details",
                recovery_questions=RECOVERY_QUESTIONS
            )

        hashed_password = generate_password_hash(new_password)
        cursor.execute(
            "UPDATE users SET password=? WHERE username=?",
            (hashed_password, username)
        )
        conn.commit()
        conn.close()

        return redirect("/?reset=1")

    return render_template(
        "forgot_password.html",
        recovery_questions=RECOVERY_QUESTIONS
    )


# ---------- HOME ----------
@app.route("/home")
def home():

    if "user" not in session:
        return redirect("/")

    username = session["user"]
    user_settings = get_user_settings(username)

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    filter_type = request.args.get("filter", "all").strip().lower()
    if filter_type not in ("all", "income", "expense"):
        filter_type = "all"

    sort_type = request.args.get("sort", "newest").strip().lower()
    if sort_type not in ("newest", "oldest", "amount_high", "amount_low"):
        sort_type = "newest"

    action = request.args.get("action", "").strip().lower()
    action_message_map = {
        "added": "Transaction added successfully.",
        "updated": "Transaction updated successfully.",
        "deleted": "Transaction deleted successfully."
    }
    action_message = action_message_map.get(action)

    cursor.execute(
        "SELECT * FROM transactions WHERE username=? ORDER BY id DESC",
        (username,)
    )

    all_transactions = cursor.fetchall()
    conn.close()

    income = sum(t[5] for t in all_transactions if t[2] == "Income")
    expense = sum(t[5] for t in all_transactions if t[2] == "Expense")
    balance = income - expense

    if filter_type == "income":
        transactions = [t for t in all_transactions if t[2] == "Income"]
    elif filter_type == "expense":
        transactions = [t for t in all_transactions if t[2] == "Expense"]
    else:
        transactions = all_transactions

    if sort_type == "oldest":
        transactions = sorted(transactions, key=lambda t: t[0])
    elif sort_type == "amount_high":
        transactions = sorted(transactions, key=lambda t: t[5], reverse=True)
    elif sort_type == "amount_low":
        transactions = sorted(transactions, key=lambda t: t[5])

    return render_template(
        "home.html",
        user=username,
        transactions=transactions,
        current_filter=filter_type,
        current_sort=sort_type,
        action_message=action_message,
        currency_symbol=user_settings["currency_symbol"],
        income=income,
        expense=expense,
        balance=balance
    )


# ---------- ADD TRANSACTION ----------
@app.route("/add_transaction", methods=["POST"])
def add_transaction():

    if "user" not in session:
        return redirect("/")

    username = session["user"]

    ttype = request.form["type"]
    category = request.form["category"]

    # Description optional
    description = request.form.get("description", "")

    amount = request.form["amount"]

    conn = sqlite3.connect("database.db")
    conn.execute(
        """
        INSERT INTO transactions(username,type,category,description,amount)
        VALUES(?,?,?,?,?)
        """,
        (username, ttype, category, description, amount)
    )
    conn.commit()
    conn.close()

    return redirect("/home?action=added")


@app.route("/delete_transaction/<int:transaction_id>", methods=["POST"])
def delete_transaction(transaction_id):

    if "user" not in session:
        return redirect("/")

    username = session["user"]
    filter_type = request.form.get("filter", "all").strip().lower()
    sort_type = request.form.get("sort", "newest").strip().lower()

    if filter_type not in ("all", "income", "expense"):
        filter_type = "all"
    if sort_type not in ("newest", "oldest", "amount_high", "amount_low"):
        sort_type = "newest"

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM transactions WHERE id=? AND username=?",
        (transaction_id, username)
    )

    conn.commit()
    conn.close()

    return redirect(
        f"/home?filter={filter_type}&sort={sort_type}&action=deleted"
    )


@app.route("/edit_transaction/<int:transaction_id>", methods=["GET", "POST"])
def edit_transaction(transaction_id):

    if "user" not in session:
        return redirect("/")

    username = session["user"]

    if request.method == "POST":
        ttype = request.form["type"].strip()
        category = request.form["category"].strip()
        description = request.form.get("description", "").strip()
        amount = request.form["amount"]

        filter_type = request.form.get("filter", "all").strip().lower()
        sort_type = request.form.get("sort", "newest").strip().lower()

        if filter_type not in ("all", "income", "expense"):
            filter_type = "all"
        if sort_type not in ("newest", "oldest", "amount_high", "amount_low"):
            sort_type = "newest"

        if ttype not in ("Income", "Expense"):
            ttype = "Expense"

        try:
            amount_value = float(amount)
            if amount_value <= 0:
                raise ValueError
        except ValueError:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM transactions WHERE id=? AND username=?",
                (transaction_id, username)
            )
            tx = cursor.fetchone()
            conn.close()

            if not tx:
                return redirect(f"/home?filter={filter_type}&sort={sort_type}")

            return render_template(
                "edit_transaction.html",
                user=username,
                transaction=tx,
                current_filter=filter_type,
                current_sort=sort_type,
                error="Amount must be greater than 0"
            )

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE transactions
            SET type=?, category=?, description=?, amount=?
            WHERE id=? AND username=?
            """,
            (ttype, category, description, amount_value, transaction_id, username)
        )
        conn.commit()
        conn.close()

        return redirect(
            f"/home?filter={filter_type}&sort={sort_type}&action=updated"
        )

    filter_type = request.args.get("filter", "all").strip().lower()
    sort_type = request.args.get("sort", "newest").strip().lower()

    if filter_type not in ("all", "income", "expense"):
        filter_type = "all"
    if sort_type not in ("newest", "oldest", "amount_high", "amount_low"):
        sort_type = "newest"

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM transactions WHERE id=? AND username=?",
        (transaction_id, username)
    )
    tx = cursor.fetchone()
    conn.close()

    if not tx:
        return redirect(f"/home?filter={filter_type}&sort={sort_type}")

    return render_template(
        "edit_transaction.html",
        user=username,
        transaction=tx,
        current_filter=filter_type,
        current_sort=sort_type
    )


# ---------- STATS ----------
@app.route("/stats")
def stats():

    if "user" not in session:
        return redirect("/")

    username = session["user"]
    user_settings = get_user_settings(username)

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM transactions WHERE username=?",
        (username,)
    )

    data = cursor.fetchall()
    conn.close()

    income = sum(t[5] for t in data if t[2] == "Income")
    expense = sum(t[5] for t in data if t[2] == "Expense")
    savings = income - expense

    return render_template(
        "stats.html",
        user=username,
        currency_symbol=user_settings["currency_symbol"],
        income=income,
        expense=expense,
        savings=savings
    )


@app.route("/stats_data")
def stats_data():

    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    username = session["user"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT type, category, amount FROM transactions WHERE username=?",
        (username,)
    )

    data = cursor.fetchall()
    conn.close()

    income = sum(row[2] for row in data if row[0] == "Income")
    expense = sum(row[2] for row in data if row[0] == "Expense")
    savings = income - expense
    savings_rate = (savings / income * 100) if income > 0 else 0

    income_categories = {}
    expense_categories = {}

    for row in data:
        ttype, category, amount = row
        category_name = (category or "Other").strip() or "Other"

        if ttype == "Income":
            income_categories[category_name] = (
                income_categories.get(category_name, 0) + amount
            )
        elif ttype == "Expense":
            expense_categories[category_name] = (
                expense_categories.get(category_name, 0) + amount
            )

    return jsonify({
        "income": round(income, 2),
        "expense": round(expense, 2),
        "savings": round(savings, 2),
        "savings_rate": round(savings_rate, 1),
        "income_categories": {
            k: round(v, 2) for k, v in income_categories.items()
        },
        "expense_categories": {
            k: round(v, 2) for k, v in expense_categories.items()
        }
    })


# ---------- FINANCIAL CONTEXT BUILDER ----------
def build_financial_context(username):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Pull ALL transaction fields
    cursor.execute(
        "SELECT id, type, category, description, amount FROM transactions WHERE username=? ORDER BY id DESC",
        (username,)
    )
    rows = cursor.fetchall()

    settings = get_user_settings(username)
    conn.close()

    sym = settings["currency_symbol"]

    # ---- Totals ----
    income_txns = [r for r in rows if r[1] == "Income"]
    expense_txns = [r for r in rows if r[1] == "Expense"]

    total_income = sum(r[4] for r in income_txns)
    total_expense = sum(r[4] for r in expense_txns)
    balance = total_income - total_expense
    savings_rate = (balance / total_income * 100) if total_income > 0 else 0
    total_txn_count = len(rows)

    # ---- Category aggregation with percentages (pie/bar chart data) ----
    income_cats = {}
    expense_cats = {}
    for r in rows:
        bucket = income_cats if r[1] == "Income" else expense_cats
        cat = (r[2] or "Other").strip() or "Other"
        bucket.setdefault(cat, {"total": 0, "count": 0})
        bucket[cat]["total"] += r[4]
        bucket[cat]["count"] += 1

    # ---- Build context text ----
    lines = [
        "=== OVERVIEW ===",
        f"Currency: {sym}",
        f"Total Income: {sym}{total_income:,.2f}",
        f"Total Expense: {sym}{total_expense:,.2f}",
        f"Current Balance (Income - Expense): {sym}{balance:,.2f}",
        f"Savings Rate: {savings_rate:.1f}%",
        f"Total Transactions: {total_txn_count} ({len(income_txns)} income, {len(expense_txns)} expense)",
    ]

    # Budget & goals
    monthly_budget = settings["monthly_budget"]
    savings_goal = settings["savings_goal"]
    if monthly_budget > 0:
        budget_used_pct = (total_expense / monthly_budget * 100) if monthly_budget > 0 else 0
        budget_remaining = monthly_budget - total_expense
        lines.append(f"\nMonthly Budget: {sym}{monthly_budget:,.2f}")
        lines.append(f"Budget Used: {sym}{total_expense:,.2f} ({budget_used_pct:.1f}%)")
        lines.append(f"Budget Remaining: {sym}{budget_remaining:,.2f}")
        if budget_used_pct >= 100:
            lines.append("WARNING: OVER BUDGET")
        elif budget_used_pct >= 80:
            lines.append("WARNING: Approaching budget limit")
    if savings_goal > 0:
        goal_progress = (balance / savings_goal * 100) if savings_goal > 0 else 0
        lines.append(f"Savings Goal: {sym}{savings_goal:,.2f}")
        lines.append(f"Savings Goal Progress: {sym}{balance:,.2f} ({goal_progress:.1f}%)")

    # ---- Income breakdown (pie chart data) ----
    if income_cats:
        lines.append("\n=== INCOME BREAKDOWN (Pie Chart Data) ===")
        for cat, info in sorted(income_cats.items(), key=lambda x: -x[1]["total"]):
            pct = (info["total"] / total_income * 100) if total_income > 0 else 0
            lines.append(f"  {cat}: {sym}{info['total']:,.2f} | {pct:.1f}% of income | {info['count']} transaction(s)")

    # ---- Expense breakdown (pie/bar chart data) ----
    if expense_cats:
        lines.append("\n=== EXPENSE BREAKDOWN (Bar/Pie Chart Data) ===")
        for cat, info in sorted(expense_cats.items(), key=lambda x: -x[1]["total"]):
            pct = (info["total"] / total_expense * 100) if total_expense > 0 else 0
            lines.append(f"  {cat}: {sym}{info['total']:,.2f} | {pct:.1f}% of expenses | {info['count']} transaction(s)")

    # ---- Statistics / Averages ----
    lines.append("\n=== STATISTICS ===")
    if income_txns:
        avg_income = total_income / len(income_txns)
        max_income = max(income_txns, key=lambda r: r[4])
        min_income = min(income_txns, key=lambda r: r[4])
        lines.append(f"Average Income Transaction: {sym}{avg_income:,.2f}")
        lines.append(f"Largest Income: {sym}{max_income[4]:,.2f} ({max_income[2]} - {max_income[3] or 'no description'})")
        lines.append(f"Smallest Income: {sym}{min_income[4]:,.2f} ({min_income[2]} - {min_income[3] or 'no description'})")
    if expense_txns:
        avg_expense = total_expense / len(expense_txns)
        max_expense = max(expense_txns, key=lambda r: r[4])
        min_expense = min(expense_txns, key=lambda r: r[4])
        lines.append(f"Average Expense Transaction: {sym}{avg_expense:,.2f}")
        lines.append(f"Largest Expense: {sym}{max_expense[4]:,.2f} ({max_expense[2]} - {max_expense[3] or 'no description'})")
        lines.append(f"Smallest Expense: {sym}{min_expense[4]:,.2f} ({min_expense[2]} - {min_expense[3] or 'no description'})")
    if total_income > 0 and total_expense > 0:
        expense_to_income = (total_expense / total_income * 100)
        lines.append(f"Expense-to-Income Ratio: {expense_to_income:.1f}%")

    # ---- Recent transactions (most recent first, max 50) ----
    recent = rows[:50]
    lines.append(f"\n=== RECENT TRANSACTIONS ({len(recent)} of {len(rows)} shown, most recent first) ===")
    for r in recent:
        desc_part = f" - {r[3]}" if r[3] else ""
        lines.append(f"  [{r[1]}] {r[2]}{desc_part}: {sym}{r[4]:,.2f}")

    return {
        "context_text": "\n".join(lines),
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "balance": round(balance, 2),
        "savings_rate": round(savings_rate, 1),
        "currency_symbol": sym,
    }


SYSTEM_PROMPT = """You are SmartBudget Advisor, a friendly personal finance assistant.

RULES:
- Use ONLY the real numbers from the financial data below. Never invent figures.
- Always use the correct currency symbol from the data.
- Bold important numbers with **asterisks**.
- Give specific, actionable advice based on the user's real finances.
- Use bullet points or numbered steps for longer answers.
- Be warm and encouraging. Celebrate good habits, gently flag concerns.
- Never show code, JSON, or technical details.
- Never give vague/generic advice — always reference actual amounts and categories.
- For spending questions: list top categories with amounts and percentages.
- For saving advice: give concrete monthly targets and timelines.
- For financial health: evaluate savings rate, expense-to-income ratio, and budget adherence.

User's financial data:
{financial_data}
"""


# ---------- ADVISOR ----------
@app.route("/advisor")
def advisor():
    if "user" not in session:
        return redirect("/")

    username = session["user"]
    fin = build_financial_context(username)
    return render_template(
        "advisor.html",
        user=username,
        income=fin["total_income"],
        expense=fin["total_expense"],
        balance=fin["balance"],
        savings_rate=fin["savings_rate"],
        currency_symbol=fin["currency_symbol"],
    )


@app.route("/advisor/chat", methods=["POST"])
def advisor_chat():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data or not data.get("message"):
        return jsonify({"error": "Message is required"}), 400

    username = session["user"]
    user_message = data["message"].strip()
    history = data.get("history", [])

    fin = build_financial_context(username)
    system_text = SYSTEM_PROMPT.format(financial_data=fin["context_text"])

    messages = [{"role": "system", "content": system_text}]
    for msg in history[-20:]:
        if msg.get("role") in ("user", "assistant") and msg.get("content"):
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

    def generate():
        try:
            resp = http_requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "repeat_penalty": 1.15,
                        "num_ctx": 2048,
                    },
                },
                stream=True,
                timeout=120,
            )
            if resp.status_code == 404:
                yield f"data: {json.dumps({'error': f'Model {OLLAMA_MODEL} not found. Run: ollama pull {OLLAMA_MODEL}'})}\n\n"
                return
            resp.raise_for_status()

            in_code_block = False
            for line in resp.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                token = chunk.get("message", {}).get("content", "")
                if token:
                    # Strip code fences and skip code block content
                    if "```" in token:
                        in_code_block = not in_code_block
                        token = token.replace("```", "")
                    if in_code_block:
                        continue
                    # Remove leftover inline code ticks
                    token = token.replace("`", "")
                    if token.strip():
                        yield f"data: {json.dumps({'token': token})}\n\n"
                if chunk.get("done"):
                    break

            yield f"data: {json.dumps({'done': True})}\n\n"

        except http_requests.ConnectionError:
            yield f"data: {json.dumps({'error': 'Cannot connect to Ollama. Please ensure Ollama is running at ' + OLLAMA_URL})}\n\n"
        except http_requests.Timeout:
            yield f"data: {json.dumps({'error': 'Request timed out. The model may be loading — please try again.'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': f'An error occurred: {str(e)}'})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/settings")
def settings():
    if "user" not in session:
        return redirect("/")

    username = session["user"]

    settings_data = get_user_settings(username)

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT type, amount FROM transactions WHERE username=?",
        (username,)
    )
    rows = cursor.fetchall()

    cursor.execute(
        "SELECT security_question FROM users WHERE username=?",
        (username,)
    )
    recovery_row = cursor.fetchone()
    conn.close()

    total_income = sum(r[1] for r in rows if r[0] == "Income")
    total_expense = sum(r[1] for r in rows if r[0] == "Expense")
    transaction_count = len(rows)

    status = request.args.get("status", "").strip().lower()
    error_code = request.args.get("error", "").strip().lower()

    status_map = {
        "reset": "All transaction data has been reset.",
        "username_updated": "Username updated successfully.",
        "password_updated": "Password updated successfully.",
        "recovery_updated": "Recovery question updated successfully."
    }

    error_map = {
        "current_password_invalid": "Current password is incorrect.",
        "username_required": "New username is required.",
        "username_same": "New username must be different.",
        "username_exists": "That username is already taken.",
        "new_password_short": "New password must be at least 6 characters.",
        "new_password_mismatch": "New password and confirmation do not match.",
        "new_password_same": "New password must be different from current password.",
        "recovery_question_invalid": "Please select a valid recovery question.",
        "recovery_answer_short": "Please provide a valid recovery answer."
    }

    success = None
    if status in status_map:
        success = status_map[status]

    error = None
    if error_code in error_map:
        error = error_map[error_code]

    return render_template(
        "settings.html",
        user=username,
        success=success,
        error=error,
        recovery_questions=RECOVERY_QUESTIONS,
        current_recovery_question=(recovery_row[0] if recovery_row else ""),
        total_income=total_income,
        total_expense=total_expense,
        transaction_count=transaction_count,
        currency_symbol=settings_data["currency_symbol"]
    )


@app.route("/reset_transactions", methods=["POST"])
def reset_transactions():
    if "user" not in session:
        return redirect("/")

    username = session["user"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM transactions WHERE username=?",
        (username,)
    )
    conn.commit()
    conn.close()

    return redirect("/settings?status=reset")


@app.route("/change_username", methods=["POST"])
def change_username():
    if "user" not in session:
        return redirect("/")

    current_username = session["user"]
    new_username = request.form.get("new_username", "").strip()
    current_password = request.form.get("current_password", "")

    if not new_username:
        return redirect("/settings?error=username_required")

    if new_username == current_username:
        return redirect("/settings?error=username_same")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, password FROM users WHERE username=?",
        (current_username,)
    )
    user = cursor.fetchone()

    if not user or not verify_password(user[1], current_password):
        conn.close()
        return redirect("/settings?error=current_password_invalid")

    try:
        cursor.execute(
            "UPDATE users SET username=? WHERE id=?",
            (new_username, user[0])
        )
        cursor.execute(
            "UPDATE transactions SET username=? WHERE username=?",
            (new_username, current_username)
        )
        cursor.execute(
            "UPDATE user_settings SET username=? WHERE username=?",
            (new_username, current_username)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return redirect("/settings?error=username_exists")

    conn.close()
    session["user"] = new_username
    return redirect("/settings?status=username_updated")


@app.route("/change_password", methods=["POST"])
def change_password():
    if "user" not in session:
        return redirect("/")

    username = session["user"]
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if len(new_password) < 6:
        return redirect("/settings?error=new_password_short")

    if new_password != confirm_password:
        return redirect("/settings?error=new_password_mismatch")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT password FROM users WHERE username=?",
        (username,)
    )
    row = cursor.fetchone()

    if not row or not verify_password(row[0], current_password):
        conn.close()
        return redirect("/settings?error=current_password_invalid")

    if verify_password(row[0], new_password):
        conn.close()
        return redirect("/settings?error=new_password_same")

    cursor.execute(
        "UPDATE users SET password=? WHERE username=?",
        (generate_password_hash(new_password), username)
    )
    conn.commit()
    conn.close()

    return redirect("/settings?status=password_updated")


@app.route("/change_recovery", methods=["POST"])
def change_recovery():
    if "user" not in session:
        return redirect("/")

    username = session["user"]
    current_password = request.form.get("current_password", "")
    security_question = request.form.get("security_question", "").strip()
    security_answer = request.form.get("security_answer", "").strip()

    if security_question not in RECOVERY_QUESTIONS:
        return redirect("/settings?error=recovery_question_invalid")

    if len(security_answer) < 2:
        return redirect("/settings?error=recovery_answer_short")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT password FROM users WHERE username=?",
        (username,)
    )
    row = cursor.fetchone()

    if not row or not verify_password(row[0], current_password):
        conn.close()
        return redirect("/settings?error=current_password_invalid")

    cursor.execute(
        "UPDATE users SET security_question=?, security_answer=? WHERE username=?",
        (
            security_question,
            generate_password_hash(security_answer.lower()),
            username
        )
    )
    conn.commit()
    conn.close()

    return redirect("/settings?status=recovery_updated")


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)

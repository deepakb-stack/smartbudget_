from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "smartbudgetsecret"


# ---------- DATABASE ----------
def init_db():

    conn = sqlite3.connect("database.db")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

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

    conn.close()


init_db()


# ---------- LOGIN ----------
@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/home")

        return render_template("login.html", error="Invalid Login")

    return render_template("login.html")


# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        try:
            conn = sqlite3.connect("database.db")
            conn.execute(
                "INSERT INTO users(username,password) VALUES(?,?)",
                (username, password)
            )
            conn.commit()
            conn.close()

            return redirect("/")

        except:
            return render_template("register.html", error="User exists")

    return render_template("register.html")


# ---------- HOME ----------
@app.route("/home")
def home():

    if "user" not in session:
        return redirect("/")

    username = session["user"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM transactions WHERE username=? ORDER BY id DESC",
        (username,)
    )

    transactions = cursor.fetchall()
    conn.close()

    income = sum(t[5] for t in transactions if t[2] == "Income")
    expense = sum(t[5] for t in transactions if t[2] == "Expense")
    balance = income - expense

    return render_template(
        "home.html",
        user=username,
        transactions=transactions,
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

    return redirect("/home")


# ---------- STATS ----------
@app.route("/stats")
def stats():

    if "user" not in session:
        return redirect("/")

    username = session["user"]

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
        income=income,
        expense=expense,
        savings=savings
    )


# ---------- OTHER PAGES ----------
@app.route("/advisor")
def advisor():
    if "user" not in session:
        return redirect("/")
    return render_template("advisor.html", user=session["user"])


@app.route("/settings")
def settings():
    if "user" not in session:
        return redirect("/")
    return render_template("settings.html", user=session["user"])


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import sqlite3
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = "playerok-2026-super-secret-key-change-me-in-production"

USDT_WALLET = "TYourTRC20WalletAddressHere1234567890"  # ← Замени!

def get_db():
    db = sqlite3.connect("playerok.db", detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            balance REAL DEFAULT 0.0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            image TEXT,
            category TEXT
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            type TEXT, -- topup, purchase, refund
            amount REAL,
            description TEXT,
            status TEXT DEFAULT 'completed',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Демо товары
    if db.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        db.executemany("""INSERT INTO products (title, description, price, image, category) VALUES (?,?,?,?,?)""", [
            ("Forza Horizon 6 + Subnautica 2", "Steam общий аккаунт | Быстрая выдача", 149, "https://picsum.photos/id/1015/400/250", "account"),
            ("R.E.P.O. Steam Аккаунт", "Общий доступ | Быстрая выдача", 109, "https://picsum.photos/id/237/400/250", "account"),
            ("Смена региона в Google Play", "Без входа в аккаунт", 90, "https://picsum.photos/id/201/400/250", "service"),
            ("Steam Аккаунт | Казахстан", "Чистый аккаунт | Полный доступ", 90, "https://picsum.photos/id/180/400/250", "account"),
            ("Black Myth: Wukong Steam", "Аккаунт с игрой | TLOU | Wukong", 119, "https://picsum.photos/id/1016/400/250", "account"),
        ])
        db.commit()
    db.close()

@app.route("/")
def index():
    db = get_db()
    products = db.execute("SELECT * FROM products").fetchall()
    db.close()
    return render_template("index.html", products=products)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password)).fetchone()
        db.close()
        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Добро пожаловать обратно!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Неверный email или пароль", "error")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        db = get_db()
        try:
            db.execute("INSERT INTO users (username, email, password) VALUES (?,?,?)", (username, email, password))
            db.commit()
            flash("Регистрация прошла успешно!", "success")
            return redirect(url_for("login"))
        except:
            flash("Пользователь с таким email уже существует", "error")
        finally:
            db.close()
    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    transactions = db.execute("SELECT * FROM transactions WHERE user_id=? ORDER BY created_at DESC", (session["user_id"],)).fetchall()
    db.close()
    return render_template("dashboard.html", user=user, transactions=transactions)

@app.route("/balance", methods=["GET", "POST"])
def balance():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        amount = float(request.form.get("amount", 0))
        if amount > 0:
            tx_id = str(uuid.uuid4())[:12].upper()
            db = get_db()
            db.execute("INSERT INTO transactions (id, user_id, type, amount, description) VALUES (?,?,?,?,?)",
                       (tx_id, session["user_id"], "topup", amount, "Пополнение баланса USDT"))
            db.commit()
            db.close()
            flash(f"Заявка на пополнение {amount} USDT создана", "success")
            return redirect(url_for("topup_pay", tx_id=tx_id))
    return render_template("balance.html")

@app.route("/topup/<tx_id>")
def topup_pay(tx_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("topup_pay.html", amount=100, wallet=USDT_WALLET, tx_id=tx_id)  # можно сделать динамику позже

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)

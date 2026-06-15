from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import uuid
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "playerok-super-secret-2026")

USDT_WALLET = os.environ.get("USDT_WALLET", "TYourTRC20WalletAddressHere1234567890")

def get_db():
    db = sqlite3.connect("playerok.db")
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
            category TEXT,
            file_link TEXT,
            created_by INTEGER,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            type TEXT,
            amount REAL,
            description TEXT,
            status TEXT DEFAULT 'completed',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Демо товары
    if db.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        db.executemany("""INSERT INTO products 
            (title, description, price, image, category, file_link) VALUES (?,?,?,?,?,?)""", [
            ("Forza Horizon 6 + Subnautica 2", "Steam общий аккаунт | Быстрая выдача", 149, "https://picsum.photos/id/1015/400/250", "Аккаунты", "Данные после оплаты"),
            ("R.E.P.O. Steam Аккаунт", "Общий доступ", 109, "https://picsum.photos/id/237/400/250", "Аккаунты", "Данные после оплаты"),
            ("Смена региона Google Play", "Без входа в аккаунт", 90, "https://picsum.photos/id/201/400/250", "Услуги", "Инструкция после оплаты"),
        ])
        db.commit()
    db.close()

# Инициализация базы
init_db()

@app.context_processor
def inject_user():
    user = None
    if "user_id" in session:
        try:
            db = get_db()
            user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
            db.close()
        except:
            pass
    return dict(user=user)

@app.route("/")
def index():
    db = get_db()
    products = db.execute("SELECT * FROM products WHERE status='active'").fetchall()
    db.close()
    return render_template("index.html", products=products)

# ====================== МНОГОЭТАПНАЯ ПРОДАЖА ======================
@app.route("/sell", methods=["GET", "POST"])
def sell_step1():
    if "user_id" not in session:
        flash("Войдите в аккаунт", "error")
        return redirect(url_for("login"))
    
    categories = ["Аккаунты", "Игры", "Услуги", "Цифровые товары", "Подписки", "Другое"]
    
    if request.method == "POST":
        session["sell_category"] = request.form.get("category")
        return redirect(url_for("sell_step2"))
    
    return render_template("sell_step1.html", categories=categories)

@app.route("/sell/step2", methods=["GET", "POST"])
def sell_step2():
    if "user_id" not in session or "sell_category" not in session:
        return redirect(url_for("sell"))
    
    if request.method == "POST":
        session["sell_title"] = request.form.get("title")
        session["sell_description"] = request.form.get("description")
        session["sell_price"] = float(request.form.get("price", 0))
        session["sell_image"] = request.form.get("image")
        return redirect(url_for("sell_step3"))
    
    return render_template("sell_step2.html", category=session.get("sell_category"))

@app.route("/sell/step3", methods=["GET", "POST"])
def sell_step3():
    if "user_id" not in session or "sell_title" not in session:
        return redirect(url_for("sell"))
    
    if request.method == "POST":
        db = get_db()
        db.execute("""INSERT INTO products 
            (title, description, price, image, category, file_link, created_by) 
            VALUES (?,?,?,?,?,?,?)""", (
                session["sell_title"],
                session["sell_description"],
                session["sell_price"],
                session["sell_image"],
                session["sell_category"],
                request.form.get("file_link"),
                session["user_id"]
            ))
        db.commit()
        db.close()
        
        # Очистка сессии
        for key in list(session.keys()):
            if key.startswith("sell_"):
                session.pop(key)
        
        flash("Товар успешно опубликован!", "success")
        return redirect(url_for("dashboard"))
    
    return render_template("sell_step3.html")

# ====================== ОСНОВНЫЕ СТРАНИЦЫ ======================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password)).fetchone()
        db.close()
        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Добро пожаловать!", "success")
            return redirect(url_for("dashboard"))
        flash("Неверный email или пароль", "error")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        db = get_db()
        try:
            db.execute("INSERT INTO users (username, email, password) VALUES (?,?,?)", 
                      (username, email, password))
            db.commit()
            flash("Регистрация успешна! Войдите в аккаунт.", "success")
            return redirect(url_for("login"))
        except:
            flash("Пользователь с таким email уже существует", "error")
        finally:
            db.close()
    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Войдите в аккаунт", "error")
        return redirect(url_for("login"))
    
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    my_products = db.execute("SELECT * FROM products WHERE created_by=? AND status='active'", 
                           (session["user_id"],)).fetchall()
    db.close()
    
    if not user:
        session.clear()
        flash("Ошибка аккаунта", "error")
        return redirect(url_for("login"))
    
    return render_template("dashboard.html", user=user, my_products=my_products)

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
                       (tx_id, session["user_id"], "topup", amount, "Пополнение USDT"))
            db.commit()
            db.close()
            flash(f"Заявка на пополнение {amount} USDT создана", "success")
            return redirect(url_for("topup_pay", tx_id=tx_id))
    return render_template("balance.html")

@app.route("/topup/<tx_id>")
def topup_pay(tx_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("topup_pay.html", amount=100, wallet=USDT_WALLET)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)

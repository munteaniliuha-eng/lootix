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
            image TEXT
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
        -- Новые таблицы для продажи товаров и чатов
        CREATE TABLE IF NOT EXISTS seller_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            image TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buyer_id INTEGER,
            seller_id INTEGER,
            product_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            sender_id INTEGER,
            message TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Демо товары (если таблица пустая)
    if db.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        db.executemany("INSERT INTO products (title, description, price, image) VALUES (?,?,?,?)", [
            ("Forza Horizon 6 + Subnautica 2", "Steam общий аккаунт | Быстрая выдача", 149, "https://picsum.photos/id/1015/400/250"),
            ("R.E.P.O. Steam Аккаунт", "Общий доступ | Быстрая выдача", 109, "https://picsum.photos/id/237/400/250"),
            ("Смена региона Google Play", "Без входа в аккаунт", 90, "https://picsum.photos/id/201/400/250"),
            ("Steam Аккаунт Казахстан", "Чистый аккаунт", 90, "https://picsum.photos/id/180/400/250"),
        ])
        db.commit()
    db.close()

# Инициализация базы при каждом запуске (важно для Render)
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
    products = db.execute("SELECT * FROM products").fetchall()
    db.close()
    return render_template("index.html", products=products)

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
            db.execute("INSERT INTO users (username, email, password) VALUES (?,?,?)", (username, email, password))
            db.commit()
            flash("Регистрация успешна! Теперь войдите.", "success")
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
# ====================== ПРОДАЖА ТОВАРОВ ======================
@app.route("/sell", methods=["GET", "POST"])
def sell():
    if "user_id" not in session:
        flash("Войдите в аккаунт, чтобы продавать", "error")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        price = float(request.form.get("price", 0))
        image = request.form.get("image", "https://picsum.photos/400/250")
        
        db = get_db()
        db.execute("""INSERT INTO products (title, description, price, image) 
                      VALUES (?,?,?,?)""", (title, description, price, image))
        db.commit()
        db.close()
        
        flash("Товар успешно опубликован!", "success")
        return redirect(url_for("dashboard"))
    
    return render_template("sell.html")

# Добавь новую таблицу для чатов (добавь в init_db())
if __name__ == "__main__":
    app.run(debug=True, port=5000)

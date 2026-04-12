from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "clothes_shop_secret_2024"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "shop.db")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static/uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'buyer',
            shop_name TEXT, shop_desc TEXT, avatar TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER, name TEXT NOT NULL, price INTEGER NOT NULL,
            category TEXT NOT NULL, subcategory TEXT NOT NULL,
            description TEXT, photo TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (seller_id) REFERENCES users(id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buyer_id INTEGER, buyer_name TEXT, phone TEXT, email TEXT,
            address TEXT, payment TEXT, total INTEGER,
            status TEXT DEFAULT 'Новый',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (buyer_id) REFERENCES users(id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER, product_id INTEGER, product_name TEXT,
            price INTEGER, size TEXT, qty INTEGER,
            FOREIGN KEY (order_id) REFERENCES orders(id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS favorites (
            user_id INTEGER, product_id INTEGER,
            PRIMARY KEY (user_id, product_id))""")

    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        demo_pw = generate_password_hash("13101977")
        c.execute("""INSERT OR IGNORE INTO users (username, email, password, role, shop_name, shop_desc)
                     VALUES (?,?,?,'admin',?,?)""",
                  ("fureosk","fureosk@shop.ru",demo_pw,"Fureoska Official","Официальный магазин одежды Fureoska"))
        c.execute("SELECT id FROM users WHERE username='fureosk'")
        sid = c.fetchone()[0]
        products = [
            # ── Мужская / Верхняя одежда ──
            ("Пуховик зимний чёрный",5999,"Мужская","Верхняя одежда","Тёплый пуховик на зиму с капюшоном","https://images.pexels.com/photos/3680219/pexels-photo-3680219.jpeg?w=400&h=400&fit=crop"),
            ("Кожаная куртка чёрная",7999,"Мужская","Верхняя одежда","Стильная кожаная куртка на молнии","https://images.pexels.com/photos/1124468/pexels-photo-1124468.jpeg?w=400&h=400&fit=crop"),
            ("Парка хаки",6499,"Мужская","Верхняя одежда","Тёплая парка с мехом и капюшоном","https://images.pexels.com/photos/6073952/pexels-photo-6073952.jpeg?w=400&h=400&fit=crop"),
            ("Бомбер серый",4999,"Мужская","Верхняя одежда","Стильный бомбер на осень-весну","https://images.pexels.com/photos/5698851/pexels-photo-5698851.jpeg?w=400&h=400&fit=crop"),
            ("Тренч бежевый",8499,"Мужская","Верхняя одежда","Классический тренчкот из плащёвки","https://images.pexels.com/photos/4937449/pexels-photo-4937449.jpeg?w=400&h=400&fit=crop"),
            ("Дутая жилетка синяя",3299,"Мужская","Верхняя одежда","Лёгкая стёганая жилетка без рукавов","https://images.pexels.com/photos/6311392/pexels-photo-6311392.jpeg?w=400&h=400&fit=crop"),
            # ── Мужская / Футболки ──
            ("Футболка белая базовая",799,"Мужская","Футболки","Базовая хлопковая футболка оверсайз","https://images.pexels.com/photos/8532616/pexels-photo-8532616.jpeg?w=400&h=400&fit=crop"),
            ("Футболка чёрная",799,"Мужская","Футболки","Классическая чёрная футболка из хлопка","https://images.pexels.com/photos/5698855/pexels-photo-5698855.jpeg?w=400&h=400&fit=crop"),
            ("Рубашка поло синяя",1299,"Мужская","Футболки","Классическая рубашка поло с воротником","https://images.pexels.com/photos/6311394/pexels-photo-6311394.jpeg?w=400&h=400&fit=crop"),
            ("Лонгслив полосатый",1499,"Мужская","Футболки","Лонгслив в морскую полоску","https://images.pexels.com/photos/5699150/pexels-photo-5699150.jpeg?w=400&h=400&fit=crop"),
            ("Футболка с принтом",999,"Мужская","Футболки","Яркая футболка с графическим принтом","https://images.pexels.com/photos/4066293/pexels-photo-4066293.jpeg?w=400&h=400&fit=crop"),
            ("Рубашка клетчатая",1799,"Мужская","Футболки","Фланелевая рубашка в клетку","https://images.pexels.com/photos/6311387/pexels-photo-6311387.jpeg?w=400&h=400&fit=crop"),
            # ── Мужская / Брюки ──
            ("Джинсы slim синие",2999,"Мужская","Брюки","Зауженные синие джинсы стретч","https://images.pexels.com/photos/1598507/pexels-photo-1598507.jpeg?w=400&h=400&fit=crop"),
            ("Джинсы чёрные",2999,"Мужская","Брюки","Классические чёрные джинсы прямого кроя","https://images.pexels.com/photos/4210866/pexels-photo-4210866.jpeg?w=400&h=400&fit=crop"),
            ("Спортивные штаны серые",1999,"Мужская","Брюки","Удобные спортивные штаны с карманами","https://images.pexels.com/photos/7679720/pexels-photo-7679720.jpeg?w=400&h=400&fit=crop"),
            ("Классические брюки чёрные",3499,"Мужская","Брюки","Строгие классические брюки для офиса","https://images.pexels.com/photos/6311600/pexels-photo-6311600.jpeg?w=400&h=400&fit=crop"),
            ("Карго брюки хаки",3299,"Мужская","Брюки","Практичные карго с множеством карманов","https://images.pexels.com/photos/6975543/pexels-photo-6975543.jpeg?w=400&h=400&fit=crop"),
            # ── Мужская / Обувь ──
            ("Кроссовки белые",4999,"Мужская","Обувь","Классические белые кроссовки на каждый день","https://images.pexels.com/photos/1464625/pexels-photo-1464625.jpeg?w=400&h=400&fit=crop"),
            ("Кожаные ботинки коричневые",7999,"Мужская","Обувь","Классические кожаные ботинки на шнурках","https://images.pexels.com/photos/267301/pexels-photo-267301.jpeg?w=400&h=400&fit=crop"),
            ("Тимберленды жёлтые",8999,"Мужская","Обувь","Легендарные ботинки из нубука","https://images.pexels.com/photos/3261069/pexels-photo-3261069.jpeg?w=400&h=400&fit=crop"),
            # ── Женская / Платья ──
            ("Летнее платье белое",2499,"Женская","Платья","Лёгкое белое платье на лето из шифона","https://images.pexels.com/photos/1536619/pexels-photo-1536619.jpeg?w=400&h=400&fit=crop"),
            ("Вечернее платье чёрное",5499,"Женская","Платья","Элегантное чёрное платье в пол","https://images.pexels.com/photos/1755428/pexels-photo-1755428.jpeg?w=400&h=400&fit=crop"),
            ("Платье в цветочек",2999,"Женская","Платья","Нежное платье с цветочным принтом","https://images.pexels.com/photos/4347773/pexels-photo-4347773.jpeg?w=400&h=400&fit=crop"),
            ("Платье-рубашка джинсовое",3299,"Женская","Платья","Стильное джинсовое платье-рубашка","https://images.pexels.com/photos/1926769/pexels-photo-1926769.jpeg?w=400&h=400&fit=crop"),
            ("Платье в горошек",2799,"Женская","Платья","Ретро-платье в горошек с поясом","https://images.pexels.com/photos/5886041/pexels-photo-5886041.jpeg?w=400&h=400&fit=crop"),
            ("Трикотажное платье бежевое",3999,"Женская","Платья","Облегающее тёплое платье из трикотажа","https://images.pexels.com/photos/6311168/pexels-photo-6311168.jpeg?w=400&h=400&fit=crop"),
            # ── Женская / Юбки ──
            ("Мини-юбка джинсовая",1499,"Женская","Юбки","Стильная джинсовая мини-юбка с пуговицами","https://images.pexels.com/photos/6311479/pexels-photo-6311479.jpeg?w=400&h=400&fit=crop"),
            ("Плиссированная юбка розовая",1999,"Женская","Юбки","Нежная миди-юбка-плиссе пастельного цвета","https://images.pexels.com/photos/6311251/pexels-photo-6311251.jpeg?w=400&h=400&fit=crop"),
            ("Юбка-карандаш чёрная",2299,"Женская","Юбки","Классическая юбка-карандаш до колена","https://images.pexels.com/photos/6311390/pexels-photo-6311390.jpeg?w=400&h=400&fit=crop"),
            ("Макси-юбка льняная",2799,"Женская","Юбки","Лёгкая длинная юбка из льна для лета","https://images.pexels.com/photos/6311327/pexels-photo-6311327.jpeg?w=400&h=400&fit=crop"),
            # ── Женская / Блузки ──
            ("Шёлковая блузка белая",2299,"Женская","Блузки","Элегантная шёлковая блузка с бантом","https://images.pexels.com/photos/6311178/pexels-photo-6311178.jpeg?w=400&h=400&fit=crop"),
            ("Блузка в полоску",1799,"Женская","Блузки","Классическая полосатая блузка оверсайз","https://images.pexels.com/photos/6311409/pexels-photo-6311409.jpeg?w=400&h=400&fit=crop"),
            ("Кружевная блузка бежевая",2999,"Женская","Блузки","Романтичная блузка с кружевными вставками","https://images.pexels.com/photos/6311263/pexels-photo-6311263.jpeg?w=400&h=400&fit=crop"),
            ("Атласная блузка зелёная",2499,"Женская","Блузки","Блузка из атласной ткани изумрудного цвета","https://images.pexels.com/photos/6311282/pexels-photo-6311282.jpeg?w=400&h=400&fit=crop"),
            # ── Женская / Обувь ──
            ("Туфли на каблуке чёрные",5999,"Женская","Обувь","Классические лодочки на каблуке 8 см","https://images.pexels.com/photos/336372/pexels-photo-336372.jpeg?w=400&h=400&fit=crop"),
            ("Белые кеды",3499,"Женская","Обувь","Лёгкие белые кеды для ежедневных прогулок","https://images.pexels.com/photos/1598508/pexels-photo-1598508.jpeg?w=400&h=400&fit=crop"),
            ("Ботильоны замшевые бежевые",6999,"Женская","Обувь","Элегантные замшевые ботильоны на каблуке","https://images.pexels.com/photos/2562992/pexels-photo-2562992.jpeg?w=400&h=400&fit=crop"),
            # ── Детская / Верхняя одежда ──
            ("Детская куртка красная",2999,"Детская","Верхняя одежда","Яркая демисезонная куртка для детей","https://images.pexels.com/photos/5560021/pexels-photo-5560021.jpeg?w=400&h=400&fit=crop"),
            ("Зимний комбинезон синий",3999,"Детская","Верхняя одежда","Тёплый зимний комбинезон с капюшоном","https://images.pexels.com/photos/3661350/pexels-photo-3661350.jpeg?w=400&h=400&fit=crop"),
            ("Ветровка детская жёлтая",1999,"Детская","Верхняя одежда","Яркая лёгкая ветровка на молнии","https://images.pexels.com/photos/6849554/pexels-photo-6849554.jpeg?w=400&h=400&fit=crop"),
            ("Пуховик детский розовый",3499,"Детская","Верхняя одежда","Тёплый пуховик для девочки","https://images.pexels.com/photos/5559986/pexels-photo-5559986.jpeg?w=400&h=400&fit=crop"),
            # ── Детская / Футболки ──
            ("Футболка с динозавром",599,"Детская","Футболки","Весёлая футболка с принтом динозавра","https://images.pexels.com/photos/6913977/pexels-photo-6913977.jpeg?w=400&h=400&fit=crop"),
            ("Футболка полосатая детская",699,"Детская","Футболки","Яркая полосатая футболка с длинным рукавом","https://images.pexels.com/photos/5560022/pexels-photo-5560022.jpeg?w=400&h=400&fit=crop"),
            ("Футболка с единорогом",799,"Детская","Футболки","Сказочная футболка с единорогом","https://images.pexels.com/photos/6913571/pexels-photo-6913571.jpeg?w=400&h=400&fit=crop"),
            ("Поло детское белое",899,"Детская","Футболки","Классическое поло для школы и прогулок","https://images.pexels.com/photos/5560018/pexels-photo-5560018.jpeg?w=400&h=400&fit=crop"),
            # ── Детская / Брюки ──
            ("Джинсы детские синие",1499,"Детская","Брюки","Удобные джинсы с эластичным поясом","https://images.pexels.com/photos/6913562/pexels-photo-6913562.jpeg?w=400&h=400&fit=crop"),
            ("Спортивные штаны детские",999,"Детская","Брюки","Мягкие спортивные штаны из флиса","https://images.pexels.com/photos/5560026/pexels-photo-5560026.jpeg?w=400&h=400&fit=crop"),
            ("Леггинсы для девочек",799,"Детская","Брюки","Удобные цветные леггинсы для активных детей","https://images.pexels.com/photos/6913563/pexels-photo-6913563.jpeg?w=400&h=400&fit=crop"),
            # ── Детская / Обувь ──
            ("Кроссовки детские синие",2499,"Детская","Обувь","Лёгкие кроссовки для активных игр","https://images.pexels.com/photos/1895574/pexels-photo-1895574.jpeg?w=400&h=400&fit=crop"),
            ("Ботинки детские коричневые",2999,"Детская","Обувь","Тёплые осенние ботинки на флисе","https://images.pexels.com/photos/5560025/pexels-photo-5560025.jpeg?w=400&h=400&fit=crop"),
        ]
        c.executemany(
            "INSERT INTO products (seller_id,name,price,category,subcategory,description,photo) VALUES (?,?,?,?,?,?,?)",
            [(sid,*p) for p in products]
        )
    conn.commit()
    conn.close()

SUBCATEGORIES = {
    "Мужская":  ["Верхняя одежда","Футболки","Брюки","Обувь"],
    "Женская":  ["Платья","Юбки","Блузки","Обувь"],
    "Детская":  ["Верхняя одежда","Футболки","Брюки","Обувь"],
}
SIZES = ["XS","S","M","L","XL","XXL"]

def current_user():
    uid = session.get("user_id")
    if not uid: return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone()
    conn.close()
    return user

def get_favorites_ids():
    user = current_user()
    if user:
        conn = get_db()
        rows = conn.execute("SELECT product_id FROM favorites WHERE user_id=?",(user["id"],)).fetchall()
        conn.close()
        return [r["product_id"] for r in rows]
    return session.get("favorites",[])

def get_cart_count():
    return sum(session.get("cart",{}).values())

def get_dark():
    return session.get("dark",False)

def get_lang():
    return session.get("lang","ru")

def get_product(pid):
    conn = get_db()
    p = conn.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone()
    conn.close()
    return p

def admin_required():
    user = current_user()
    return user and user["role"] == "admin"

def get_admin_stats(conn):
    return {
        "users":    conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "sellers":  conn.execute("SELECT COUNT(*) FROM users WHERE role='seller'").fetchone()[0],
        "buyers":   conn.execute("SELECT COUNT(*) FROM users WHERE role='buyer'").fetchone()[0],
        "products": conn.execute("SELECT COUNT(*) FROM products").fetchone()[0],
        "orders":   conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
        "revenue":  conn.execute("SELECT COALESCE(SUM(total),0) FROM orders").fetchone()[0],
    }

# AUTH
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email    = request.form["email"].strip()
        password = request.form["password"]
        role     = request.form["role"]
        shop_name= request.form.get("shop_name","").strip()
        shop_desc= request.form.get("shop_desc","").strip()
        if not username or not email or not password:
            flash("Заполните все поля","error"); return redirect(url_for("register"))
        pw_hash = generate_password_hash(password)
        conn = get_db()
        try:
            conn.execute("INSERT INTO users (username,email,password,role,shop_name,shop_desc) VALUES (?,?,?,?,?,?)",
                         (username,email,pw_hash,role,shop_name or username,shop_desc))
            conn.commit()
            user = conn.execute("SELECT * FROM users WHERE username=?",(username,)).fetchone()
            session["user_id"] = user["id"]
            flash("Аккаунт создан!","success"); return redirect(url_for("home"))
        except sqlite3.IntegrityError:
            flash("Такой логин или email уже занят","error"); return redirect(url_for("register"))
        finally: conn.close()
    return render_template("register.html",dark=get_dark())

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        login_val = request.form["login"].strip()
        password  = request.form["password"]
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? OR email=?",(login_val,login_val)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"],password):
            session["user_id"] = user["id"]
            flash("Добро пожаловать!","success"); return redirect(url_for("home"))
        flash("Неверный логин или пароль","error"); return redirect(url_for("login"))
    return render_template("login.html",dark=get_dark())

@app.route("/logout")
def logout():
    session.pop("user_id",None); return redirect(url_for("landing"))

# PROFILE
@app.route("/profile")
def profile():
    user = current_user()
    if not user: return redirect(url_for("login"))
    if user["role"] == "admin": return redirect(url_for("admin_dashboard"))
    conn = get_db()
    if user["role"] == "seller":
        products_list = conn.execute("SELECT * FROM products WHERE seller_id=? ORDER BY created_at DESC",(user["id"],)).fetchall()
        total_sales = conn.execute("""SELECT COALESCE(SUM(oi.price*oi.qty),0) as total FROM order_items oi
            JOIN products p ON oi.product_id=p.id WHERE p.seller_id=?""",(user["id"],)).fetchone()["total"]
        orders_count = conn.execute("""SELECT COUNT(DISTINCT oi.order_id) as cnt FROM order_items oi
            JOIN products p ON oi.product_id=p.id WHERE p.seller_id=?""",(user["id"],)).fetchone()["cnt"]
        recent_orders = conn.execute("""SELECT o.*,oi.product_name,oi.size,oi.qty,oi.price as item_price,o.id as order_id
            FROM orders o JOIN order_items oi ON o.id=oi.order_id JOIN products p ON oi.product_id=p.id
            WHERE p.seller_id=? ORDER BY o.created_at DESC LIMIT 10""",(user["id"],)).fetchall()
        conn.close()
        return render_template("profile_seller.html",user=user,products=products_list,
            total_sales=total_sales,orders_count=orders_count,recent_orders=recent_orders,
            cart_count=get_cart_count(),dark=get_dark())
    else:
        orders = conn.execute("SELECT * FROM orders WHERE buyer_id=? ORDER BY created_at DESC",(user["id"],)).fetchall()
        orders_with_items = [{"order":o,"lines":conn.execute("SELECT * FROM order_items WHERE order_id=?",(o["id"],)).fetchall()} for o in orders]
        fav_ids = [r["product_id"] for r in conn.execute("SELECT product_id FROM favorites WHERE user_id=?",(user["id"],)).fetchall()]
        fav_products = [p for p in [conn.execute("SELECT * FROM products WHERE id=?",(fid,)).fetchone() for fid in fav_ids] if p]
        conn.close()
        return render_template("profile_buyer.html",user=user,orders=orders_with_items,
            favorites=fav_products,cart_count=get_cart_count(),dark=get_dark())

@app.route("/profile/edit", methods=["GET","POST"])
def profile_edit():
    user = current_user()
    if not user: return redirect(url_for("login"))
    if request.method == "POST":
        conn = get_db()
        conn.execute("UPDATE users SET shop_name=?,shop_desc=? WHERE id=?",
                     (request.form.get("shop_name","").strip(),request.form.get("shop_desc","").strip(),user["id"]))
        conn.commit(); conn.close()
        flash("Профиль обновлён","success"); return redirect(url_for("profile"))
    return render_template("profile_edit.html",user=user,dark=get_dark())

@app.route("/seller/<int:uid>")
def seller_page(uid):
    conn = get_db()
    seller = conn.execute("SELECT * FROM users WHERE id=? AND role='seller'",(uid,)).fetchone()
    if not seller: conn.close(); return redirect(url_for("home"))
    products_list = conn.execute("SELECT * FROM products WHERE seller_id=? ORDER BY created_at DESC",(uid,)).fetchall()
    conn.close()
    return render_template("seller_page.html",seller=seller,products=products_list,
        favorites=get_favorites_ids(),cart_count=get_cart_count(),dark=get_dark(),current_user=current_user())

@app.route("/product/delete/<int:pid>")
def product_delete(pid):
    user = current_user()
    if not user or user["role"] != "seller": return redirect(url_for("home"))
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id=? AND seller_id=?",(pid,user["id"]))
    conn.commit(); conn.close()
    flash("Товар удалён","success"); return redirect(url_for("profile"))

# LANDING PAGE
@app.route("/")
def landing():
    return render_template("welcome.html", user=current_user(), lang=get_lang())

@app.route("/set-lang/<lang_code>")
def set_lang(lang_code):
    if lang_code in ("ru","en"):
        session["lang"] = lang_code
    return redirect(request.referrer or url_for("landing"))

# MAIN SHOP
@app.route("/shop")
def home():
    category    = request.args.get("category","Все")
    subcategory = request.args.get("subcategory","Все")
    search      = request.args.get("search","").strip()
    sort        = request.args.get("sort","")
    conn = get_db()
    query = "SELECT * FROM products WHERE 1=1"; params = []
    if category != "Все": query += " AND category=?"; params.append(category)
    if subcategory != "Все": query += " AND subcategory=?"; params.append(subcategory)
    if search: query += " AND name LIKE ?"; params.append(f"%{search}%")
    query += " ORDER BY price ASC" if sort=="asc" else " ORDER BY price DESC" if sort=="desc" else " ORDER BY id DESC"
    products_list = conn.execute(query,params).fetchall()
    conn.close()
    return render_template("index.html",products=products_list,current=category,
        subcategory=subcategory,subcats=SUBCATEGORIES.get(category,[]) if category!="Все" else [],
        search=search,favorites=get_favorites_ids(),cart_count=get_cart_count(),
        sort=sort,dark=get_dark(),user=current_user(),lang=get_lang())

@app.route("/toggle-theme")
def toggle_theme():
    session["dark"] = not session.get("dark",False)
    return redirect(request.referrer or url_for("home"))

@app.route("/add", methods=["GET","POST"])
def add():
    user = current_user()
    if not user or user["role"] not in ("seller","admin"):
        flash("Добавлять товары могут только продавцы","error"); return redirect(url_for("login"))
    if request.method == "POST":
        photo = request.files.get("photo"); photo_path = None
        if photo and photo.filename:
            filename = f"{user['id']}_{int(datetime.now().timestamp())}_{photo.filename}"
            photo.save(os.path.join(UPLOAD_FOLDER,filename)); photo_path = f"/static/uploads/{filename}"
        conn = get_db()
        conn.execute("INSERT INTO products (seller_id,name,price,category,subcategory,description,photo) VALUES (?,?,?,?,?,?,?)",
                     (user["id"],request.form["name"],int(request.form["price"]),
                      request.form["category"],request.form["subcategory"],request.form["description"],photo_path))
        conn.commit(); conn.close()
        flash("Товар добавлен!","success"); return redirect(url_for("home"))
    return render_template("add.html",subcategories=SUBCATEGORIES,cart_count=get_cart_count(),dark=get_dark(),user=user)

@app.route("/product/<int:pid>")
def product_page(pid):
    product = get_product(pid)
    if not product: return redirect(url_for("home"))
    conn = get_db()
    seller = conn.execute("SELECT * FROM users WHERE id=?",(product["seller_id"],)).fetchone()
    conn.close()
    return render_template("product.html",product=product,sizes=SIZES,
        favorites=get_favorites_ids(),cart_count=get_cart_count(),dark=get_dark(),seller=seller,user=current_user())

@app.route("/cart")
def cart():
    cart_data = session.get("cart",{}); items=[]; total=0
    for key,qty in cart_data.items():
        pid,size = (key.split("_")+[""])[:2]; product = get_product(int(pid))
        if product:
            subtotal = product["price"]*qty
            items.append({"product":product,"qty":qty,"size":size,"subtotal":subtotal,"key":key}); total+=subtotal
    return render_template("cart.html",items=items,total=total,cart_count=get_cart_count(),dark=get_dark(),user=current_user())

@app.route("/cart/add/<int:pid>")
def cart_add(pid):
    if not current_user():
        flash("Войдите в аккаунт, чтобы добавить товар в корзину","error")
        return redirect(url_for("login"))
    size = request.args.get("size","M"); cart = session.get("cart",{})
    key = f"{pid}_{size}"; cart[key] = cart.get(key,0)+1; session["cart"] = cart
    return redirect(request.referrer or url_for("home"))

@app.route("/cart/remove/<key>")
def cart_remove(key):
    cart = session.get("cart",{}); cart.pop(key,None); session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/cart/clear")
def cart_clear():
    session["cart"] = {}; return redirect(url_for("cart"))

def send_order_notification(order_id, buyer_name, phone, email, address, payment, total, items):
    """Отправляет уведомление о новом заказе на почту администратора."""
    import smtplib
    from email.mime.text import MIMEText

    # ──── НАСТРОЙТЕ ЭТИ ПАРАМЕТРЫ ────
    ADMIN_EMAIL   = "fureoskwork@gmail.com"   # куда приходят уведомления
    SMTP_HOST     = "smtp.gmail.com"    # или smtp.gmail.com, smtp.mail.ru
    SMTP_PORT     = 587
    SMTP_USER     = "fureoskwork@gmail.com"   # ваш email-логин
    SMTP_PASSWORD = "mzhz cahr udkq qinu"        # пароль приложения
    # ─────────────────────────────────

    lines = "\n".join(
        f"  • {it['product']['name']} ({it['size']}) × {it['qty']} = {it['subtotal']} ₽"
        for it in items
    )
    body = (
        f"🛒 Новый заказ #{order_id}\n\n"
        f"Покупатель : {buyer_name}\n"
        f"Телефон    : {phone}\n"
        f"Email      : {email}\n"
        f"Адрес      : {address}\n"
        f"Оплата     : {payment}\n\n"
        f"Состав:\n{lines}\n\n"
        f"Итого: {total} ₽"
    )
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"[Fureoska] Новый заказ #{order_id} на {total} ₽"
    msg["From"]    = SMTP_USER
    msg["To"]      = ADMIN_EMAIL
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASSWORD)
            s.send_message(msg)
    except Exception as e:
        app.logger.error(f"[email] Не удалось отправить уведомление: {e}")

@app.route("/order", methods=["GET","POST"])
def order():
    user = current_user()
    if not user:
        flash("Войдите в аккаунт, чтобы оформить заказ","error")
        return redirect(url_for("login"))
    cart_data = session.get("cart",{}); items=[]; total=0
    for key,qty in cart_data.items():
        pid,size = (key.split("_")+[""])[:2]; product = get_product(int(pid))
        if product:
            subtotal = product["price"]*qty
            items.append({"product":product,"qty":qty,"size":size,"subtotal":subtotal,"pid":int(pid)}); total+=subtotal
    if request.method == "POST":
        conn = get_db()
        conn.execute("INSERT INTO orders (buyer_id,buyer_name,phone,email,address,payment,total) VALUES (?,?,?,?,?,?,?)",
                     (user["id"],request.form["name"],request.form["phone"],
                      request.form["email"],request.form["address"],request.form["payment"],total))
        order_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        for item in items:
            conn.execute("INSERT INTO order_items (order_id,product_id,product_name,price,size,qty) VALUES (?,?,?,?,?,?)",
                         (order_id,item["pid"],item["product"]["name"],item["product"]["price"],item["size"],item["qty"]))
        conn.commit(); conn.close(); session["cart"] = {}
        # Отправляем email-уведомление администратору
        send_order_notification(order_id,request.form["name"],request.form["phone"],
            request.form["email"],request.form["address"],request.form["payment"],total,items)
        return render_template("order_success.html",name=request.form.get("name"),dark=get_dark(),user=current_user())
    return render_template("order.html",items=items,total=total,cart_count=get_cart_count(),dark=get_dark(),user=current_user())

@app.route("/favorites")
def favorites():
    user = current_user(); conn = get_db()
    fav_ids = [r["product_id"] for r in conn.execute("SELECT product_id FROM favorites WHERE user_id=?",(user["id"],)).fetchall()] if user else session.get("favorites",[])
    fav_products = [p for p in [conn.execute("SELECT * FROM products WHERE id=?",(fid,)).fetchone() for fid in fav_ids] if p]
    conn.close()
    return render_template("favorites.html",products=fav_products,cart_count=get_cart_count(),dark=get_dark(),user=user,favorites=fav_ids)

@app.route("/favorites/toggle/<int:pid>")
def favorites_toggle(pid):
    user = current_user()
    if user:
        conn = get_db()
        if conn.execute("SELECT 1 FROM favorites WHERE user_id=? AND product_id=?",(user["id"],pid)).fetchone():
            conn.execute("DELETE FROM favorites WHERE user_id=? AND product_id=?",(user["id"],pid))
        else:
            conn.execute("INSERT INTO favorites (user_id,product_id) VALUES (?,?)",(user["id"],pid))
        conn.commit(); conn.close()
    else:
        favs = session.get("favorites",[])
        if pid in favs: favs.remove(pid)
        else: favs.append(pid)
        session["favorites"] = favs
    return redirect(request.referrer or url_for("home"))

# ADMIN
@app.route("/admin/reset-products")
def admin_reset_products():
    if not admin_required():
        return redirect(url_for("home"))
    conn = get_db()
    conn.execute("DELETE FROM products")
    conn.commit()
    conn.close()
    init_db()
    flash("Товары сброшены и загружены заново с правильными фото", "success")
    return redirect(url_for("admin_products"))

@app.route("/admin")
def admin_dashboard():
    if not admin_required(): flash("Доступ запрещён","error"); return redirect(url_for("home"))
    conn = get_db()
    stats = get_admin_stats(conn)
    recent_orders = conn.execute("""SELECT o.*,u.username as buyer_username FROM orders o
        LEFT JOIN users u ON o.buyer_id=u.id ORDER BY o.created_at DESC LIMIT 5""").fetchall()
    recent_users = conn.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT 5").fetchall()
    conn.close()
    return render_template("admin.html",section="dashboard",stats=stats,
        recent_orders=recent_orders,recent_users=recent_users,dark=get_dark(),user=current_user())

@app.route("/admin/users")
def admin_users():
    if not admin_required(): return redirect(url_for("home"))
    conn = get_db()
    users = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    stats = get_admin_stats(conn); conn.close()
    return render_template("admin.html",section="users",users=users,stats=stats,dark=get_dark(),user=current_user())

@app.route("/admin/products")
def admin_products():
    if not admin_required(): return redirect(url_for("home"))
    conn = get_db()
    products = conn.execute("""SELECT p.*,u.username as seller_name FROM products p
        LEFT JOIN users u ON p.seller_id=u.id ORDER BY p.created_at DESC""").fetchall()
    stats = get_admin_stats(conn); conn.close()
    return render_template("admin.html",section="products",products=products,stats=stats,dark=get_dark(),user=current_user())

@app.route("/admin/orders")
def admin_orders():
    if not admin_required(): return redirect(url_for("home"))
    conn = get_db()
    orders = conn.execute("""SELECT o.*,u.username as buyer_username FROM orders o
        LEFT JOIN users u ON o.buyer_id=u.id ORDER BY o.created_at DESC""").fetchall()
    orders_with_items = [{"order":o,"lines":conn.execute("SELECT * FROM order_items WHERE order_id=?",(o["id"],)).fetchall()} for o in orders]
    stats = get_admin_stats(conn); conn.close()
    return render_template("admin.html",section="orders",orders=orders_with_items,stats=stats,dark=get_dark(),user=current_user())

@app.route("/admin/users/role/<int:uid>", methods=["POST"])
def admin_user_role(uid):
    if not admin_required(): return redirect(url_for("home"))
    new_role = request.form.get("role")
    if new_role in ("buyer","seller","admin"):
        conn = get_db(); conn.execute("UPDATE users SET role=? WHERE id=?",(new_role,uid)); conn.commit(); conn.close()
        flash("Роль обновлена","success")
    return redirect(url_for("admin_users"))

@app.route("/admin/users/delete/<int:uid>")
def admin_user_delete(uid):
    if not admin_required(): return redirect(url_for("home"))
    conn = get_db()
    conn.execute("DELETE FROM favorites WHERE user_id=?",(uid,))
    conn.execute("DELETE FROM products WHERE seller_id=?",(uid,))
    conn.execute("DELETE FROM users WHERE id=?",(uid,))
    conn.commit(); conn.close()
    flash("Пользователь удалён","success"); return redirect(url_for("admin_users"))

@app.route("/admin/products/delete/<int:pid>")
def admin_product_delete(pid):
    if not admin_required(): return redirect(url_for("home"))
    conn = get_db(); conn.execute("DELETE FROM products WHERE id=?",(pid,)); conn.commit(); conn.close()
    flash("Товар удалён","success"); return redirect(url_for("admin_products"))

@app.route("/admin/products/edit/<int:pid>", methods=["GET","POST"])
def admin_product_edit(pid):
    if not admin_required(): return redirect(url_for("home"))
    conn = get_db()
    if request.method == "POST":
        conn.execute("UPDATE products SET name=?,price=?,category=?,subcategory=?,description=? WHERE id=?",
                     (request.form["name"],int(request.form["price"]),request.form["category"],
                      request.form["subcategory"],request.form["description"],pid))
        conn.commit(); conn.close(); flash("Товар обновлён","success"); return redirect(url_for("admin_products"))
    product = conn.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone()
    stats = get_admin_stats(conn); conn.close()
    return render_template("admin.html",section="product_edit",product=product,
        subcategories=SUBCATEGORIES,stats=stats,dark=get_dark(),user=current_user())

@app.route("/admin/orders/status/<int:oid>", methods=["POST"])
def admin_order_status(oid):
    if not admin_required(): return redirect(url_for("home"))
    status = request.form.get("status")
    if status in ("Новый","В обработке","Отправлен","Доставлен","Отменён"):
        conn = get_db(); conn.execute("UPDATE orders SET status=? WHERE id=?",(status,oid)); conn.commit(); conn.close()
        flash("Статус заказа обновлён","success")
    return redirect(url_for("admin_orders"))

if __name__ == "__main__":
    init_db()
    conn = get_db()
    pw = generate_password_hash("13101977")
    updated = conn.execute("UPDATE users SET password=?,role='admin' WHERE username='fureosk'",(pw,)).rowcount
    if updated == 0:
        conn.execute("""INSERT INTO users (username,email,password,role,shop_name,shop_desc)
                        VALUES ('fureosk','fureosk@shop.ru',?,'admin','Fureoska Official','Официальный магазин одежды Fureoska')""",(pw,))
    conn.commit(); conn.close()
    app.run(debug=True)

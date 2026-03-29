from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "clothes_shop_secret_2024"
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB = "shop.db"

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
            ("Пуховик зимний чёрный",5999,"Мужская","Верхняя одежда","Тёплый пуховик на зиму с капюшоном","https://images.unsplash.com/photo-1608063615781-e2ef8c73d114?w=400"),
            ("Кожаная куртка чёрная",7999,"Мужская","Верхняя одежда","Стильная кожаная куртка на молнии","https://images.unsplash.com/photo-1551028719-00167b16eac5?w=400"),
            ("Парка хаки",6499,"Мужская","Верхняя одежда","Тёплая парка с мехом и капюшоном","https://images.unsplash.com/photo-1539533018447-63fcce2678e3?w=400"),
            ("Бомбер серый",4999,"Мужская","Верхняя одежда","Стильный бомбер на осень-весну","https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=400"),
            ("Тренч бежевый",8499,"Мужская","Верхняя одежда","Классический тренчкот из плащёвки","https://images.unsplash.com/photo-1544441893-675973e31985?w=400"),
            ("Дутая жилетка синяя",3299,"Мужская","Верхняя одежда","Лёгкая стёганая жилетка без рукавов","https://images.unsplash.com/photo-1574180566232-aaad1b5b8450?w=400"),
            ("Футболка белая базовая",799,"Мужская","Футболки","Базовая хлопковая футболка оверсайз","https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400"),
            ("Футболка чёрная",799,"Мужская","Футболки","Классическая чёрная футболка из хлопка","https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=400"),
            ("Рубашка поло синяя",1299,"Мужская","Футболки","Классическая рубашка поло с воротником","https://images.unsplash.com/photo-1625910513962-881aafdf5e84?w=400"),
            ("Лонгслив полосатый",1499,"Мужская","Футболки","Лонгслив в морскую полоску","https://images.unsplash.com/photo-1618354691373-d851c5c3a990?w=400"),
            ("Футболка с принтом",999,"Мужская","Футболки","Яркая футболка с графическим принтом","https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=400"),
            ("Рубашка клетчатая",1799,"Мужская","Футболки","Фланелевая рубашка в клетку","https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=400"),
            ("Джинсы slim синие",2999,"Мужская","Брюки","Зауженные синие джинсы стретч","https://images.unsplash.com/photo-1542272604-787c3835535d?w=400"),
            ("Джинсы чёрные",2999,"Мужская","Брюки","Классические чёрные джинсы прямого кроя","https://images.unsplash.com/photo-1604176354204-9268737828e4?w=400"),
            ("Спортивные штаны серые",1999,"Мужская","Брюки","Удобные спортивные штаны с карманами","https://images.unsplash.com/photo-1552902865-b72c031ac5ea?w=400"),
            ("Классические брюки чёрные",3499,"Мужская","Брюки","Строгие классические брюки для офиса","https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=400"),
            ("Карго брюки хаки",3299,"Мужская","Брюки","Практичные карго с множеством карманов","https://images.unsplash.com/photo-1517445312882-bc9910d016b7?w=400"),
            ("Кроссовки белые",4999,"Мужская","Обувь","Классические белые кроссовки на каждый день","https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400"),
            ("Кожаные ботинки коричневые",7999,"Мужская","Обувь","Классические кожаные ботинки на шнурках","https://images.unsplash.com/photo-1608256246200-53e635b5b65f?w=400"),
            ("Тимберленды жёлтые",8999,"Мужская","Обувь","Легендарные ботинки из нубука","https://images.unsplash.com/photo-1520639888713-7851133b1ed0?w=400"),
            ("Летнее платье белое",2499,"Женская","Платья","Лёгкое белое платье на лето из шифона","https://images.unsplash.com/photo-1623609163859-ca93c959b98a?w=400"),
            ("Вечернее платье чёрное",5499,"Женская","Платья","Элегантное чёрное платье в пол","https://images.unsplash.com/photo-1539008835657-9e8e9680c956?w=400"),
            ("Платье в цветочек",2999,"Женская","Платья","Нежное платье с цветочным принтом","https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=400"),
            ("Платье-рубашка джинсовое",3299,"Женская","Платья","Стильное джинсовое платье-рубашка","https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400"),
            ("Платье в горошек",2799,"Женская","Платья","Ретро-платье в горошек с поясом","https://images.unsplash.com/photo-1550639525-c97d455acf70?w=400"),
            ("Трикотажное платье бежевое",3999,"Женская","Платья","Облегающее тёплое платье из трикотажа","https://images.unsplash.com/photo-1434389677669-e08b4cac3105?w=400"),
            ("Мини-юбка джинсовая",1499,"Женская","Юбки","Стильная джинсовая мини-юбка с пуговицами","https://images.unsplash.com/photo-1582142839970-2b9e04b60f65?w=400"),
            ("Плиссированная юбка розовая",1999,"Женская","Юбки","Нежная миди-юбка-плиссе пастельного цвета","https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=400"),
            ("Юбка-карандаш чёрная",2299,"Женская","Юбки","Классическая юбка-карандаш до колена","https://images.unsplash.com/photo-1577900232427-18219b9166a0?w=400"),
            ("Макси-юбка льняная",2799,"Женская","Юбки","Лёгкая длинная юбка из льна для лета","https://images.unsplash.com/photo-1612336307429-8a898d10e223?w=400"),
            ("Шёлковая блузка белая",2299,"Женская","Блузки","Элегантная шёлковая блузка с бантом","https://images.unsplash.com/photo-1564257631407-4deb1f99d992?w=400"),
            ("Блузка в полоску",1799,"Женская","Блузки","Классическая полосатая блузка оверсайз","https://images.unsplash.com/photo-1598554747436-c9293d6a588f?w=400"),
            ("Кружевная блузка бежевая",2999,"Женская","Блузки","Романтичная блузка с кружевными вставками","https://images.unsplash.com/photo-1503944583220-79d8926ad5e2?w=400"),
            ("Атласная блузка зелёная",2499,"Женская","Блузки","Блузка из атласной ткани изумрудного цвета","https://images.unsplash.com/photo-1485462537746-965f33f7f6a7?w=400"),
            ("Туфли на каблуке чёрные",5999,"Женская","Обувь","Классические лодочки на каблуке 8 см","https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=400"),
            ("Белые кеды",3499,"Женская","Обувь","Лёгкие белые кеды для ежедневных прогулок","https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?w=400"),
            ("Ботильоны замшевые бежевые",6999,"Женская","Обувь","Элегантные замшевые ботильоны на каблуке","https://images.unsplash.com/photo-1512441786607-a7e53e1c048f?w=400"),
            ("Детская куртка красная",2999,"Детская","Верхняя одежда","Яркая демисезонная куртка для детей","https://images.unsplash.com/photo-1503944583220-79d8926ad5e2?w=400"),
            ("Зимний комбинезон синий",3999,"Детская","Верхняя одежда","Тёплый зимний комбинезон с капюшоном","https://images.unsplash.com/photo-1545291730-faff8ca1d4b0?w=400"),
            ("Ветровка детская жёлтая",1999,"Детская","Верхняя одежда","Яркая лёгкая ветровка на молнии","https://images.unsplash.com/photo-1471286174890-9c112ffca5b4?w=400"),
            ("Пуховик детский розовый",3499,"Детская","Верхняя одежда","Тёплый пуховик для девочки","https://images.unsplash.com/photo-1604671801908-6f0c6a092c05?w=400"),
            ("Футболка с динозавром",599,"Детская","Футболки","Весёлая футболка с принтом динозавра","https://images.unsplash.com/photo-1519278409-1f56fdda7fe5?w=400"),
            ("Футболка полосатая детская",699,"Детская","Футболки","Яркая полосатая футболка с длинным рукавом","https://images.unsplash.com/photo-1622290291468-a28f7a7dc6a8?w=400"),
            ("Футболка с единорогом",799,"Детская","Футболки","Сказочная футболка с единорогом","https://images.unsplash.com/photo-1503342394128-c104d54dba01?w=400"),
            ("Поло детское белое",899,"Детская","Футболки","Классическое поло для школы и прогулок","https://images.unsplash.com/photo-1555689502-c4b22d76c56f?w=400"),
            ("Джинсы детские синие",1499,"Детская","Брюки","Удобные джинсы с эластичным поясом","https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=400"),
            ("Спортивные штаны детские",999,"Детская","Брюки","Мягкие спортивные штаны из флиса","https://images.unsplash.com/photo-1552902865-b72c031ac5ea?w=400"),
            ("Леггинсы для девочек",799,"Детская","Брюки","Удобные цветные леггинсы для активных детей","https://images.unsplash.com/photo-1518831959646-742c3a14ebf7?w=400"),
            ("Кроссовки детские синие",2499,"Детская","Обувь","Лёгкие кроссовки для активных игр","https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400"),
            ("Ботинки детские коричневые",2999,"Детская","Обувь","Тёплые осенние ботинки на флисе","https://images.unsplash.com/photo-1608256246200-53e635b5b65f?w=400"),
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
    session.pop("user_id",None); return redirect(url_for("home"))

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

# MAIN
@app.route("/")
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
        sort=sort,dark=get_dark(),user=current_user())

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

@app.route("/order", methods=["GET","POST"])
def order():
    cart_data = session.get("cart",{}); items=[]; total=0
    for key,qty in cart_data.items():
        pid,size = (key.split("_")+[""])[:2]; product = get_product(int(pid))
        if product:
            subtotal = product["price"]*qty
            items.append({"product":product,"qty":qty,"size":size,"subtotal":subtotal,"pid":int(pid)}); total+=subtotal
    if request.method == "POST":
        user = current_user(); conn = get_db()
        conn.execute("INSERT INTO orders (buyer_id,buyer_name,phone,email,address,payment,total) VALUES (?,?,?,?,?,?,?)",
                     (user["id"] if user else None,request.form["name"],request.form["phone"],
                      request.form["email"],request.form["address"],request.form["payment"],total))
        order_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        for item in items:
            conn.execute("INSERT INTO order_items (order_id,product_id,product_name,price,size,qty) VALUES (?,?,?,?,?,?)",
                         (order_id,item["pid"],item["product"]["name"],item["product"]["price"],item["size"],item["qty"]))
        conn.commit(); conn.close(); session["cart"] = {}
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

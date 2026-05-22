from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, g
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import secrets

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv не установлен — переменные берутся из окружения

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit

# ── Безопасность: берём из переменных окружения ──────────────
_secret = os.environ.get("SECRET_KEY")
if not _secret:
    _secret_file = os.path.join(BASE_DIR if 'BASE_DIR' in dir() else os.path.dirname(os.path.abspath(__file__)), ".secret_key")
    try:
        _secret = open(_secret_file).read().strip()
    except FileNotFoundError:
        _secret = secrets.token_hex(32)
        open(_secret_file, "w").write(_secret)
app.secret_key = _secret
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
if not ADMIN_PASSWORD:
    import warnings; warnings.warn("ADMIN_PASSWORD env var is not set! Using insecure default.")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "shop.db")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static/uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

PER_PAGE = 12  # товаров на страницу

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

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

    # Проверяем, пуста ли таблица товаров
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        # 1. Создаем или проверяем админа fureosk, чтобы получить его ID (sid)
        demo_pw = generate_password_hash(ADMIN_PASSWORD)
        c.execute("""INSERT OR IGNORE INTO users (username, email, password, role, shop_name, shop_desc)
                     VALUES (?,?,?,'admin',?,?)""",
                  ("fureosk", "fureosk@shop.ru", demo_pw, "Fureoska Official", "Официальный магазин одежды Fureoska"))
        
        c.execute("SELECT id FROM users WHERE username='fureosk'")
        sid = c.fetchone()[0]

        # 2. Полный список всех ваших товаров (50 штук)
        products = [
            # ── МУЖСКАЯ КОЛЛЕКЦИЯ (20 товаров) ───────────────────────────────────────
            ("Пуховик зимний чёрный",     5999, "Мужская", "Верхняя одежда", "Тёплый пуховик на зиму с капюшоном", "https://images.unsplash.com/photo-1544923246-77307dd654cb?w=500&auto=format&fit=crop&q=80"),
            ("Кожаная куртка чёрная",     7999, "Мужская", "Верхняя одежда", "Стильная кожаная куртка-косуха на молнии", "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=500&auto=format&fit=crop&q=80"),
            ("Парка хаки",                6499, "Мужская", "Верхняя одежда", "Тёплая удлиненная парка с капюшоном", "https://images.unsplash.com/photo-1548883354-7622d03aca27?w=500&auto=format&fit=crop&q=80"),
            ("Бомбер серый",              4999, "Мужская", "Верхняя одежда", "Стильный трикотажный бомбер на осень-весну", "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=500&auto=format&fit=crop&q=80"),
            ("Тренч бежевый",             8499, "Мужская", "Верхняя одежда", "Классический тренчкот из плотной плащёвки", "https://images.unsplash.com/photo-1593533814274-2f090dfd13cc?w=500&auto=format&fit=crop&q=80"),
            ("Дутая жилетка синяя",       3299, "Мужская", "Верхняя одежда", "Лёгкая стёганая жилетка без рукавов", "https://images.unsplash.com/photo-1620138546344-7b2c0b05133d?w=500&auto=format&fit=crop&q=80"),
            
            ("Футболка белая базовая",     799,  "Мужская", "Футболки",       "Базовая хлопковая футболка на вешалке", "https://images.unsplash.com/photo-1581655353564-df123a1eb820?w=500&auto=format&fit=crop&q=80"),
            ("Футболка чёрная",            799,  "Мужская", "Футболки",       "Классическая чёрная футболка из хлопка", "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=500&auto=format&fit=crop&q=80"),
            ("Рубашка поло синяя",        1299, "Мужская", "Футболки",       "Классическая тенниска поло с воротником", "https://images.unsplash.com/photo-1586363104862-3a5e2ab60d99?w=500&auto=format&fit=crop&q=80"),
            ("Лонгслив полосатый",        1499, "Мужская", "Футболки",       "Стильный лонгслив в черно-белую полоску", "https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91?w=500&auto=format&fit=crop&q=80"),
            ("Футболка с принтом",         999,  "Мужская", "Футболки",       "Черная футболка с ярким графическим принтом скелета", "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?w=500&auto=format&fit=crop&q=80"),
            ("Рубашка клетчатая",         1799, "Мужская", "Футболки",       "Классическая рубашка на вешалках in магазине", "https://images.unsplash.com/photo-1512436991641-6745cdb1723f?w=500&auto=format&fit=crop&q=80"),
            
            ("Джинсы slim синие",         2999, "Мужская", "Брюки",          "Зауженные синие рваные джинсы деним", "https://images.unsplash.com/photo-1542272604-787c3835535d?w=500&auto=format&fit=crop&q=80"),
            ("Джинсы чёрные",             2999, "Мужская", "Брюки",          "Классические чёрные джинсы прямого кроя", "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=500&auto=format&fit=crop&q=80"),
            ("Спортивные штаны серые",    1999, "Мужская", "Брюки",          "Удобные трикотажные джоггеры для спорта", "https://images.unsplash.com/photo-1551854838-212c50b4c184?w=500&auto=format&fit=crop&q=80"),
            ("Классические брюки чёрные", 3499, "Мужская", "Брюки",          "Строгие тёмные брюки из костюмной ткани", "https://images.unsplash.com/photo-1617113913973-f11265813496?w=500&auto=format&fit=crop&q=80"),
            ("Карго брюки хаки",          3299, "Мужская", "Брюки",          "Мужской строгий костюм тройка с брюками", "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=500&auto=format&fit=crop&q=80"),
            
            ("Кроссовки белые",           4999, "Мужская", "Обувь",          "Повседневные замшевые кроссовки на подошве", "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=500&auto=format&fit=crop&q=80"),
            ("Кожаные ботинки коричневые", 7999, "Мужская", "Обувь",          "Классические кожаные туфли дерби на шнуровке", "https://images.unsplash.com/photo-1533867617858-e7b97e060509?w=500&auto=format&fit=crop&q=80"),
            ("Тимберленды жёлтые",        8999, "Мужская", "Обувь",          "Легендарные высокие ботинки из нубука", "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500&auto=format&fit=crop&q=80"),

            # ── ЖЕНСКАЯ КОЛЛЕКЦИЯ (17 товаров) ───────────────────────────────────────
            ("Летнее платье белое",       2499, "Женская", "Платья",         "Лёгкое белое платье с узором", "https://images.unsplash.com/photo-1612336307429-8a898d10e223?w=500&auto=format&fit=crop&q=80"),
            ("Вечернее платье чёрное",    5499, "Женская", "Платья",         "Элегантное чёрное вечернее платье", "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=500&auto=format&fit=crop&q=80"),
            ("Платье в цветочек",         2999, "Женская", "Платья",         "Нежное летящее платье с принтом", "https://images.unsplash.com/photo-1496747611176-843222e1e57c?w=500&auto=format&fit=crop&q=80"),
            ("Платье-рубашка джинсовое",  3299, "Женская", "Платья",         "Повседневное синее платье-рубашка", "https://images.unsplash.com/photo-1585487000160-6ebcfceb0d03?w=500&auto=format&fit=crop&q=80"),
            ("Платье в горошек",          2799, "Женская", "Платья",         "Яркое желтое платье в горошек в ретро-стиле", "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=500&auto=format&fit=crop&q=80"),
            ("Трикотажное платье бежевое", 3999, "Женская", "Платья",         "Объемный тёплый вязаный свитер белого цвета", "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?w=500&auto=format&fit=crop&q=80"),
            
            ("Мини-юбка джинсовая",       1499, "Женская", "Юбки",           "Стильная джинсовая юбка на пуговицах", "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=500&auto=format&fit=crop&q=80"),
            ("Плиссированная юбка розовая", 1999, "Женская", "Юбки",         "Воздушная юбка плиссе нежно-розового цвета", "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=500&auto=format&fit=crop&q=80"),
            ("Юбка-карандаш чёрная",      2299, "Женская", "Юбки",           "Классическая деловая юбка до колена", "https://images.unsplash.com/photo-1591348278863-a8fb3887e2aa?w=500&auto=format&fit=crop&q=80"),
            ("Макси-юбка льняная",        2799, "Женская", "Юбки",           "Лёгкая длинная желтая юбка макси", "https://images.unsplash.com/photo-1509551388413-e18d0ac5d495?w=500&auto=format&fit=crop&q=80"),
            
            ("Шёлковая блузка белая",     2299, "Женская", "Блузки",         "Классическая белая блузка-рубашка из хлопка", "https://images.unsplash.com/photo-1603252109303-2751441dd157?w=500&auto=format&fit=crop&q=80"),
            ("Блузка в полоску",          1799, "Женская", "Блузки",         "Легкая повседневная кофта в полоску", "https://images.unsplash.com/photo-1598554889165-8139a49f2883?w=500&auto=format&fit=crop&q=80"),
            ("Кружевная блузка бежевая",  2999, "Женская", "Блузки",         "Нежная розовая блуза свободного кроя", "https://images.unsplash.com/photo-1551163943-3f6a855d1153?w=500&auto=format&fit=crop&q=80"),
            ("Атласная блузка зелёная",   2499, "Женская", "Блузки",         "Блузка из шелковистого изумрудного атласа", "https://images.unsplash.com/photo-1618244972963-dbee1a7edc95?w=500&auto=format&fit=crop&q=80"),
            
            ("Туфли на каблуке чёрные",   5999, "Женская", "Обувь",          "Элегантные красные замшевые туфли", "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=500&auto=format&fit=crop&q=80"),
            ("Белые кеды",                3499, "Женская", "Обувь",          "Минималистичные белые кожаные кеды", "https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=500&auto=format&fit=crop&q=80"),
            ("Ботильоны замшевые бежевые", 6999, "Женская", "Обувь",          "Осенние бежевые ботильоны на каблуке", "https://images.unsplash.com/photo-1605812383198-0597977963b8?w=500&auto=format&fit=crop&q=80"),

            # ── ДЕТСКАЯ КОЛЛЕКЦИЯ (13 товаров) ───────────────────────────────────────
            ("Детская куртка красная",    2999, "Детская", "Верхняя одежда", "Яркая куртка для девочки розового цвета", "https://images.unsplash.com/photo-1621466550398-df80522b9343?w=500&auto=format&fit=crop&q=80"),
            ("Зимний комбинезон синий",   3999, "Детская", "Верхняя одежда", "Тёплый плотный слитный комбинезон", "https://images.unsplash.com/photo-1540479859555-17af45c78a62?w=500&auto=format&fit=crop&q=80"),
            ("Ветровка детская жёлтая",   1999, "Детская", "Верхняя одежда", "Уютный вязаный детский желтый свитер", "https://images.unsplash.com/photo-1519457431-44ccd64a579b?w=500&auto=format&fit=crop&q=80"),
            ("Пуховик детский розовый",   3499, "Детская", "Верхняя одежда", "Плотный зимний костюм: куртка и штаны", "https://images.unsplash.com/photo-1611428813653-aa206c998586?w=500&auto=format&fit=crop&q=80"),
            
            ("Футболка с динозавром",      599,  "Детская", "Футболки",       "Мягкий детский свитшот серого цвета", "https://images.unsplash.com/photo-1503919545889-aef636e10ad4?w=500&auto=format&fit=crop&q=80"),
            ("Футболка полосатая детская",  699,  "Детская", "Футболки",       "Детская белая футболка из тонкого хлопка", "https://images.unsplash.com/photo-1607453813894-22ec15143337?w=500&auto=format&fit=crop&q=80"),
            ("Futболка с единорогом",      799,  "Детская", "Футболки",       "Летний костюм: футболка и шорты", "https://images.unsplash.com/photo-1565791380713-1756b9a05343?w=500&auto=format&fit=crop&q=80"),
            ("Поло детское белое",         899,  "Детская", "Футболки",       "Рубашка-поло с коротким рукавом", "https://images.unsplash.com/photo-1519278409-1f56fdda7bf5?w=500&auto=format&fit=crop&q=80"),
            
            ("Джинсы детские синие",      1499, "Детская", "Брюки",          "Классические детские синие джинсы прямого кроя", "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=500&auto=format&fit=crop&q=80"),
            ("Спортивные штаны детские",   999,  "Детская", "Брюки",          "Удобные трикотажные спортивные штанишки", "https://images.unsplash.com/photo-1551854838-212c50b4c184?w=500&auto=format&fit=crop&q=80"),
            ("Леггинсы для девочек",       799,  "Детская", "Брюки",          "Детские джинсовые шорты на теплую погоду", "https://images.unsplash.com/photo-1519457431-44ccd64a579b?w=500&auto=format&fit=crop&q=80"),
            
            ("Кроссовки детские синие",   2499, "Детская", "Обувь",          "Удобные беговые детские кроссовки", "https://images.unsplash.com/photo-1514989940723-e8e5163ccbe8?w=500&auto=format&fit=crop&q=80"),
            ("Ботинки детские коричневые", 2999, "Детская", "Обувь",          "Прочные кожаные детские ботинки на шнурках", "https://images.unsplash.com/photo-1608256246200-53e635b5b65f?w=500&auto=format&fit=crop&q=80"),
        ]

        # 3. Загружаем весь список в базу данных
        c.executemany(
            "INSERT INTO products (seller_id,name,price,category,subcategory,description,photo) VALUES (?,?,?,?,?,?,?)",
            [(sid, *p) for p in products]
        )
            
    conn.commit()
    conn.close()

SUBCATEGORIES = {
    "Мужская":  ["Верхняя одежда","Футболки","Брюки","Обувь"],
    "Женская":  ["Платья","Юбки","Блузки","Обувь"],
    "Детская":  ["Верхняя одежда","Футболки","Брюки","Обувь"],
}
SIZES_CLOTHING = ["XS", "S", "M", "L", "XL", "XXL"]
SIZES_SHOES_MEN     = ["40", "41", "42", "43", "44", "45", "46"]
SIZES_SHOES_WOMEN   = ["35", "36", "37", "38", "39", "40", "41"]
SIZES_SHOES_KIDS    = ["28", "29", "30", "31", "32", "33", "34", "35"]

def get_sizes_for_product(product):
    """Возвращает список размеров в зависимости от категории и подкатегории."""
    if product and product["subcategory"] == "Обувь":
        cat = product["category"]
        if cat == "Мужская":   return SIZES_SHOES_MEN
        if cat == "Женская":   return SIZES_SHOES_WOMEN
        if cat == "Детская":   return SIZES_SHOES_KIDS
    return SIZES_CLOTHING

# ── CSRF защита ──────────────────────────────────────────────
def generate_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]

def validate_csrf():
    token = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
    if not token or token != session.get("csrf_token"):
        return False
    return True

app.jinja_env.globals["csrf_token"] = generate_csrf_token

# ── Вспомогательные функции ───────────────────────────────────
def current_user():
    """Return the logged-in user, cached in Flask g for the duration of the request."""
    if "_current_user" not in g:
        uid = session.get("user_id")
        if not uid:
            g._current_user = None
        else:
            conn = get_db()
            g._current_user = conn.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone()
            conn.close()
    return g._current_user

def get_favorites_ids():
    user = current_user()
    if user:
        conn = get_db()
        rows = conn.execute("SELECT product_id FROM favorites WHERE user_id=?",(user["id"],)).fetchall()
        conn.close()
        return [r["product_id"] for r in rows]
    return session.get("favorites",[])

def get_cart_count():
    try:
        return sum(int(v) for v in session.get("cart",{}).values())
    except (TypeError, ValueError):
        return 0

def get_theme():
    return session.get("theme","light")

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

# ── EMAIL ────────────────────────────────────────────────────
SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USER     = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
ADMIN_EMAIL   = os.environ.get("ADMIN_EMAIL", "")

def send_email(to, subject, body):
    import smtplib
    from email.mime.text import MIMEText
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"]    = SMTP_USER
        msg["To"]      = to
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASSWORD)
            s.send_message(msg)
    except Exception as e:
        app.logger.error(f"[email] Ошибка отправки на {to}: {e}")

def notify_order(order_id, buyer_name, buyer_email, phone, address, payment, total, items, sellers_info, delivery_method="courier"):
    delivery_labels = {
        "courier": "Курьер (1–3 дня)",
        "pickup":  "Самовывоз из магазина",
        "post":    "Почта России (3–7 дней)",
    }
    delivery_label = delivery_labels.get(delivery_method, delivery_method)

    lines = "\n".join(
        f"  • {it['product']['name']} ({it['size']}) × {it['qty']} = {it['product']['price'] * it['qty']} ₽"
        for it in items
    )

    buyer_body = (
        f"Здравствуйте, {buyer_name}!\n\n"
        f"Ваш заказ #{order_id} принят и скоро будет обработан.\n\n"
        f"━━━ СОСТАВ ЗАКАЗА ━━━\n{lines}\n\n"
        f"Итого: {total} ₽\n\n"
        f"━━━ ДОСТАВКА ━━━\n"
        f"Способ доставки: {delivery_label}\n"
        f"Адрес: {address}\n\n"
        f"━━━ ОПЛАТА ━━━\n"
        f"Способ оплаты: {payment}\n\n"
        f"━━━ КОНТАКТЫ ━━━\n"
        f"Телефон: {phone}\n"
        f"Email: {buyer_email}\n\n"
        f"Следить за статусом заказа можно в личном кабинете на сайте Fureoska.\n\n"
        f"Спасибо за покупку! 🎉"
    )
    send_email(buyer_email, f"[Fureoska] Ваш заказ #{order_id} принят", buyer_body)

    admin_body = (
        f"Новый заказ #{order_id}\n\n"
        f"ПОКУПАТЕЛЬ\n"
        f"Имя: {buyer_name}\n"
        f"Телефон: {phone}\n"
        f"Email: {buyer_email}\n\n"
        f"ДОСТАВКА\n"
        f"Способ: {delivery_label}\n"
        f"Адрес: {address}\n\n"
        f"ОПЛАТА\n"
        f"Способ: {payment}\n\n"
        f"СОСТАВ ЗАКАЗА\n{lines}\n\n"
        f"Итого: {total} ₽"
    )
    send_email(ADMIN_EMAIL, f"[Fureoska] Новый заказ #{order_id} на {total} ₽", admin_body)

    for seller_email, seller_name, seller_items in sellers_info:
        sl = "\n".join(f"  • {it['product']['name']} ({it['size']}) × {it['qty']}" for it in seller_items)
        seller_body = (
            f"Здравствуйте, {seller_name}!\n\n"
            f"Купили ваш товар! Заказ #{order_id}.\n\n"
            f"СОСТАВ (ваши товары)\n{sl}\n\n"
            f"ДОСТАВКА\n"
            f"Способ: {delivery_label}\n"
            f"Адрес: {address}\n\n"
            f"ПОКУПАТЕЛЬ\n"
            f"Имя: {buyer_name}\n"
            f"Телефон: {phone}\n"
            f"Email: {buyer_email}"
        )
        send_email(seller_email, f"[Fureoska] Купили ваш товар! Заказ #{order_id}", seller_body)

def notify_status_change(order_id, buyer_email, buyer_name, new_status, address="", payment="", delivery_method=""):
    """Уведомление покупателю при смене статуса заказа."""
    status_msg = {
        "В обработке": "Ваш заказ принят в обработку.",
        "Отправлен":   "Ваш заказ отправлен! Ожидайте доставку.",
        "Доставлен":   "Ваш заказ доставлен. Спасибо за покупку!",
        "Отменён":     "К сожалению, ваш заказ был отменён.",
    }
    delivery_labels = {
        "courier": "Курьер",
        "pickup":  "Самовывоз",
        "post":    "Почта России",
    }
    text = status_msg.get(new_status, f"Статус изменён: {new_status}")
    delivery_info = ""
    if address:
        dl = delivery_labels.get(delivery_method, delivery_method) if delivery_method else ""
        delivery_info = f"\n━━━ ДОСТАВКА ━━━\n"
        if dl:
            delivery_info += f"Способ: {dl}\n"
        delivery_info += f"Адрес: {address}\n"
    payment_info = f"\nСпособ оплаты: {payment}\n" if payment else ""
    send_email(buyer_email, f"[Fureoska] Заказ #{order_id}: {new_status}",
        f"Здравствуйте, {buyer_name}!\n\n{text}\n\nНомер заказа: #{order_id}\n"
        f"{delivery_info}{payment_info}\n"
        f"Следить за статусом можно в личном кабинете.")

def get_admin_stats(conn):
    return {
        "users":    conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "sellers":  conn.execute("SELECT COUNT(*) FROM users WHERE role='seller'").fetchone()[0],
        "buyers":   conn.execute("SELECT COUNT(*) FROM users WHERE role='buyer'").fetchone()[0],
        "products": conn.execute("SELECT COUNT(*) FROM products").fetchone()[0],
        "orders":   conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
        "revenue":  conn.execute("SELECT COALESCE(SUM(total),0) FROM orders").fetchone()[0],
    }

# ── AUTH ──────────────────────────────────────────────────────
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        if not validate_csrf():
            flash("Ошибка безопасности, попробуйте снова","error"); return redirect(url_for("register"))
        username = request.form["username"].strip()
        email    = request.form["email"].strip()
        password = request.form["password"]
        role     = request.form["role"]
        if role not in ("buyer", "seller"):
            role = "buyer"
        shop_name= request.form.get("shop_name","").strip()
        shop_desc= request.form.get("shop_desc","").strip()
        if not username or not email or not password:
            flash("Заполните все поля","error"); return redirect(url_for("register"))
        if len(password) < 6:
            flash("Пароль должен быть не короче 6 символов","error"); return redirect(url_for("register"))
        import re
        if not re.match(r'^[a-zA-Zа-яА-ЯёЁ0-9_]{3,30}$', username):
            flash("Логин: буквы (латиница или кириллица), цифры и _, от 3 до 30 символов","error"); return redirect(url_for("register"))
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
    return render_template("register.html",theme=get_theme(),lang=get_lang())

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if not validate_csrf():
            flash("Ошибка безопасности","error"); return redirect(url_for("login"))
        login_val = request.form["login"].strip()
        password  = request.form["password"]
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? OR email=?",(login_val,login_val)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"],password):
            session["user_id"] = user["id"]
            flash("Добро пожаловать!","success"); return redirect(url_for("home"))
        flash("Неверный логин или пароль","error"); return redirect(url_for("login"))
    return render_template("login.html",theme=get_theme(),lang=get_lang())

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("cart", None)
    session.pop("favorites", None)
    return redirect(url_for("landing"))

# ── PROFILE ───────────────────────────────────────────────────
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
            cart_count=get_cart_count(),theme=get_theme(),lang=get_lang())
    else:
        orders = conn.execute("SELECT * FROM orders WHERE buyer_id=? ORDER BY created_at DESC",(user["id"],)).fetchall()
        orders_with_items = [{"order":o,"lines":conn.execute("SELECT * FROM order_items WHERE order_id=?",(o["id"],)).fetchall()} for o in orders]
        fav_ids = [r["product_id"] for r in conn.execute("SELECT product_id FROM favorites WHERE user_id=?",(user["id"],)).fetchall()]
        fav_products = [p for p in [conn.execute("SELECT * FROM products WHERE id=?",(fid,)).fetchone() for fid in fav_ids] if p]
        conn.close()
        return render_template("profile_buyer.html",user=user,orders=orders_with_items,
            favorites=fav_products,cart_count=get_cart_count(),theme=get_theme(),lang=get_lang())

@app.route("/profile/edit", methods=["GET","POST"])
def profile_edit():
    user = current_user()
    if not user: return redirect(url_for("login"))
    if request.method == "POST":
        if not validate_csrf():
            flash("Ошибка безопасности","error"); return redirect(url_for("profile_edit"))
        conn = get_db()

        # Смена имени пользователя
        new_username = request.form.get("username","").strip()
        if new_username and new_username != user["username"]:
            import re
            if not re.match(r'^[a-zA-Zа-яА-ЯёЁ0-9_]{3,30}$', new_username):
                flash("Имя пользователя: только латиница, цифры и _, от 3 до 30 символов","error")
                conn.close(); return redirect(url_for("profile_edit"))
            try:
                conn.execute("UPDATE users SET username=? WHERE id=?",(new_username, user["id"]))
            except sqlite3.IntegrityError:
                flash("Это имя пользователя уже занято","error")
                conn.close(); return redirect(url_for("profile_edit"))

        # Смена email
        new_email = request.form.get("email","").strip()
        if new_email and new_email != user["email"]:
            try:
                conn.execute("UPDATE users SET email=? WHERE id=?",(new_email, user["id"]))
            except sqlite3.IntegrityError:
                flash("Этот email уже занят","error")
                conn.close(); return redirect(url_for("profile_edit"))

        # Данные магазина (продавец/админ)
        if user["role"] in ("seller","admin"):
            conn.execute("UPDATE users SET shop_name=?,shop_desc=? WHERE id=?",
                         (request.form.get("shop_name","").strip(),
                          request.form.get("shop_desc","").strip(), user["id"]))

        # Смена пароля
        current_password = request.form.get("current_password","")
        new_password = request.form.get("new_password","")
        confirm_password = request.form.get("confirm_password","")
        if new_password or current_password:
            if not current_password:
                flash("Для смены пароля введите текущий пароль","error")
                conn.close(); return redirect(url_for("profile_edit"))
            if not check_password_hash(user["password"], current_password):
                flash("Текущий пароль указан неверно","error")
                conn.close(); return redirect(url_for("profile_edit"))
            if len(new_password) < 6:
                flash("Новый пароль должен содержать минимум 6 символов","error")
                conn.close(); return redirect(url_for("profile_edit"))
            if new_password != confirm_password:
                flash("Новые пароли не совпадают","error")
                conn.close(); return redirect(url_for("profile_edit"))
            conn.execute("UPDATE users SET password=? WHERE id=?",
                         (generate_password_hash(new_password), user["id"]))

        conn.commit(); conn.close()
        flash("Профиль обновлён ✓","success"); return redirect(url_for("profile"))
    return render_template("profile_edit.html",user=user,theme=get_theme(),lang=get_lang())

@app.route("/seller/<int:uid>")
def seller_page(uid):
    conn = get_db()
    seller = conn.execute("SELECT * FROM users WHERE id=? AND role IN ('seller','admin')",(uid,)).fetchone()
    if not seller: conn.close(); return redirect(url_for("home"))
    products_list = conn.execute("SELECT * FROM products WHERE seller_id=? ORDER BY created_at DESC",(uid,)).fetchall()
    conn.close()
    return render_template("seller_page.html",seller=seller,products=products_list,
        favorites=get_favorites_ids(),cart_count=get_cart_count(),theme=get_theme(),lang=get_lang(),current_user=current_user())

@app.route("/product/delete/<int:pid>", methods=["POST"])
def product_delete(pid):
    user = current_user()
    if not user or user["role"] not in ("seller","admin"): return redirect(url_for("home"))
    if not validate_csrf():
        flash("Ошибка безопасности","error"); return redirect(url_for("profile"))
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id=? AND seller_id=?",(pid,user["id"]))
    conn.commit(); conn.close()
    flash("Товар удалён","success"); return redirect(url_for("profile"))

# ── LANDING ───────────────────────────────────────────────────
@app.route("/")
def landing():
    return render_template("welcome.html", user=current_user(), lang=get_lang())

@app.route("/set-lang/<lang_code>")
def set_lang(lang_code):
    if lang_code in ("ru","en"):
        session["lang"] = lang_code
    return redirect(request.referrer or url_for("landing"))

# ── MAIN SHOP с пагинацией ────────────────────────────────────
@app.route("/shop")
def home():
    category    = request.args.get("category","Все")
    subcategory = request.args.get("subcategory","Все")
    search      = request.args.get("search","").strip()
    sort        = request.args.get("sort","")
    price_min   = request.args.get("price_min","").strip()
    price_max   = request.args.get("price_max","").strip()
    try:
        page = max(1, int(request.args.get("page", "1") or 1))
    except (ValueError, TypeError):
        page = 1

    conn = get_db()
    query = "SELECT * FROM products WHERE 1=1"; params = []
    if category != "Все": query += " AND category=?"; params.append(category)
    if subcategory != "Все": query += " AND subcategory=?"; params.append(subcategory)
    if search:
        query += " AND (name LIKE ? OR description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if price_min.isdigit(): query += " AND price >= ?"; params.append(int(price_min))
    if price_max.isdigit(): query += " AND price <= ?"; params.append(int(price_max))

    count_query = query.replace("SELECT *", "SELECT COUNT(*)", 1)
    total_count = conn.execute(count_query, params).fetchone()[0]

    query += " ORDER BY price ASC" if sort=="asc" else " ORDER BY price DESC" if sort=="desc" else " ORDER BY id DESC"
    query += f" LIMIT {PER_PAGE} OFFSET {(page-1)*PER_PAGE}"
    products_list = conn.execute(query, params).fetchall()
    conn.close()

    total_pages = max(1, (total_count + PER_PAGE - 1) // PER_PAGE)

    return render_template("index.html",products=products_list,current=category,
        subcategory=subcategory,subcats=SUBCATEGORIES.get(category,[]) if category!="Все" else [],
        search=search,favorites=get_favorites_ids(),cart_count=get_cart_count(),
        sort=sort,price_min=price_min,price_max=price_max,theme=get_theme(),user=current_user(),lang=get_lang(),
        page=page,total_pages=total_pages,total_count=total_count)

@app.route("/toggle-theme")
def toggle_theme():
    themes = ["light","dark","pink"]
    current = session.get("theme","light")
    next_idx = (themes.index(current) + 1) % len(themes)
    session["theme"] = themes[next_idx]
    return redirect(request.referrer or url_for("home"))

@app.route("/set-theme/<theme_name>")
def set_theme(theme_name):
    if theme_name in ("light","dark","pink"):
        session["theme"] = theme_name
    return redirect(request.referrer or url_for("home"))

# ── ADD PRODUCT ───────────────────────────────────────────────
@app.route("/add", methods=["GET","POST"])
def add():
    user = current_user()
    if not user or user["role"] not in ("seller","admin"):
        flash("Добавлять товары могут только продавцы","error"); return redirect(url_for("login"))
    if request.method == "POST":
        if not validate_csrf():
            flash("Ошибка безопасности","error"); return redirect(url_for("add"))
        photo_path = None
        photo = request.files.get("photo")
        if photo and photo.filename:
            if allowed_file(photo.filename):
                filename = secure_filename(f"{user['id']}_{int(datetime.now().timestamp())}_{photo.filename}")
                photo.save(os.path.join(UPLOAD_FOLDER, filename))
                photo_path = f"/static/uploads/{filename}"
            else:
                flash("Недопустимый формат. Используйте PNG, JPG, GIF или WEBP","error")
                return redirect(url_for("add"))
        conn = get_db()
        conn.execute("INSERT INTO products (seller_id,name,price,category,subcategory,description,photo) VALUES (?,?,?,?,?,?,?)",
                     (user["id"],request.form["name"],int(request.form["price"]),
                      request.form["category"],request.form["subcategory"],request.form["description"],photo_path))
        conn.commit(); conn.close()
        flash("Товар добавлен!","success"); return redirect(url_for("home"))
    return render_template("add.html",subcategories=SUBCATEGORIES,cart_count=get_cart_count(),theme=get_theme(),user=user,lang=get_lang())

# ── PRODUCT PAGE ──────────────────────────────────────────────
@app.route("/product/<int:pid>")
def product_page(pid):
    product = get_product(pid)
    if not product: return redirect(url_for("home"))
    conn = get_db()
    seller = conn.execute("SELECT * FROM users WHERE id=?",(product["seller_id"],)).fetchone()
    conn.close()
    sizes = get_sizes_for_product(product)
    default_size = sizes[len(sizes)//2] if sizes else "M"
    return render_template("product.html",product=product,sizes=sizes,default_size=default_size,
        favorites=get_favorites_ids(),cart_count=get_cart_count(),theme=get_theme(),seller=seller,user=current_user(),lang=get_lang())

# ── CART ──────────────────────────────────────────────────────
@app.route("/cart")
def cart():
    cart_data = session.get("cart",{}); items=[]; total=0
    for key,qty in cart_data.items():
        parts = key.split("_", 1); pid = parts[0]; size = parts[1] if len(parts) > 1 else ""
        product = get_product(int(pid))
        if product:
            subtotal = product["price"]*qty
            items.append({"product":product,"qty":qty,"size":size,"subtotal":subtotal,"key":key}); total+=subtotal
    return render_template("cart.html",items=items,total=total,cart_count=get_cart_count(),theme=get_theme(),user=current_user(),lang=get_lang())

@app.route("/cart/add/<int:pid>", methods=["GET","POST"])
def cart_add(pid):
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if not current_user():
        if is_ajax:
            return jsonify({"ok": False, "redirect": url_for("login"), "msg": "Войдите в аккаунт"})
        flash("Войдите в аккаунт, чтобы добавить товар в корзину","error")
        return redirect(url_for("login"))
    size = request.args.get("size") or request.form.get("size","M")
    cart = session.get("cart",{})
    key = f"{pid}_{size}"; cart[key] = cart.get(key,0)+1; session["cart"] = cart
    if is_ajax:
        return jsonify({"ok": True, "count": sum(cart.values()), "msg": "Добавлено в корзину!"})
    return redirect(request.referrer or url_for("home"))

@app.route("/cart/remove/<key>", methods=["GET","POST"])
def cart_remove(key):
    cart = session.get("cart",{}); cart.pop(key,None); session["cart"] = cart
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True, "count": sum(cart.values())})
    return redirect(url_for("cart"))

@app.route("/cart/update/<key>", methods=["GET","POST"])
def cart_update(key):
    qty = request.args.get("qty") or request.form.get("qty","1")
    cart = session.get("cart", {})
    if str(qty).isdigit() and 0 < int(qty) <= 99: cart[key] = int(qty)
    elif qty == "0": cart.pop(key, None)
    session["cart"] = cart
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True, "count": sum(cart.values())})
    return redirect(url_for("cart"))

@app.route("/cart/clear", methods=["GET","POST"])
def cart_clear():
    session["cart"] = {}
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True, "count": 0})
    return redirect(url_for("cart"))

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html", theme=get_theme(), user=current_user(), lang=get_lang()), 404

@app.errorhandler(413)
def file_too_large(e):
    flash("Файл слишком большой. Максимальный размер — 5 МБ.", "error")
    return redirect(request.referrer or url_for("home"))

# ── ORDER ─────────────────────────────────────────────────────
@app.route("/order", methods=["GET","POST"])
def order():
    user = current_user()
    if not user:
        flash("Войдите в аккаунт, чтобы оформить заказ","error"); return redirect(url_for("login"))
    cart_data = session.get("cart",{}); items=[]; total=0
    for key,qty in cart_data.items():
        parts = key.split("_", 1); pid = parts[0]; size = parts[1] if len(parts) > 1 else ""
        product = get_product(int(pid))
        if product:
            subtotal = product["price"]*qty
            items.append({"product":product,"qty":qty,"size":size,"subtotal":subtotal,"pid":int(pid)}); total+=subtotal
    if not items:
        flash("Корзина пуста — добавьте товары перед оформлением заказа","error")
        return redirect(url_for("cart"))
    if request.method == "POST":
        if not validate_csrf():
            flash("Ошибка безопасности","error"); return redirect(url_for("order"))
        buyer_name      = request.form["name"]
        buyer_email     = request.form["email"]
        phone_code      = request.form.get("phone_code", "+7")
        phone_raw       = request.form.get("phone", "")
        phone           = f"{phone_code} {phone_raw}".strip()
        address         = request.form["address"]
        payment         = request.form["payment"]
        delivery_method = request.form.get("delivery_type", "courier")
        conn = get_db()
        conn.execute("INSERT INTO orders (buyer_id,buyer_name,phone,email,address,payment,total) VALUES (?,?,?,?,?,?,?)",
                     (user["id"],buyer_name,phone,buyer_email,address,payment,total))
        order_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        for item in items:
            conn.execute("INSERT INTO order_items (order_id,product_id,product_name,price,size,qty) VALUES (?,?,?,?,?,?)",
                         (order_id,item["pid"],item["product"]["name"],item["product"]["price"],item["size"],item["qty"]))
        conn.commit()
        sellers_map = {}
        for item in items:
            sid = item["product"]["seller_id"]
            if sid not in sellers_map:
                seller = conn.execute("SELECT username, email, shop_name FROM users WHERE id=?",(sid,)).fetchone()
                if seller:
                    sellers_map[sid] = {"email":seller["email"],"name":seller["shop_name"] or seller["username"],"items":[]}
            if sid in sellers_map:
                sellers_map[sid]["items"].append(item)
        conn.close()
        session["cart"] = {}
        sellers_info = [(s["email"],s["name"],s["items"]) for s in sellers_map.values()]
        notify_order(order_id,buyer_name,buyer_email,phone,address,payment,total,items,sellers_info,delivery_method)
        return render_template("order_success.html",name=buyer_name,theme=get_theme(),user=current_user(),lang=get_lang())
    return render_template("order.html",items=items,total=total,cart_count=get_cart_count(),theme=get_theme(),user=current_user(),lang=get_lang())

# ── FAVORITES ─────────────────────────────────────────────────
@app.route("/favorites")
def favorites():
    user = current_user(); conn = get_db()
    fav_ids = [r["product_id"] for r in conn.execute("SELECT product_id FROM favorites WHERE user_id=?",(user["id"],)).fetchall()] if user else session.get("favorites",[])
    fav_products = [p for p in [conn.execute("SELECT * FROM products WHERE id=?",(fid,)).fetchone() for fid in fav_ids] if p]
    conn.close()
    return render_template("favorites.html",products=fav_products,cart_count=get_cart_count(),theme=get_theme(),user=user,favorites=fav_ids,lang=get_lang())

@app.route("/favorites/toggle/<int:pid>")
def favorites_toggle(pid):
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    user = current_user()
    is_fav = False
    if user:
        conn = get_db()
        existing = conn.execute("SELECT 1 FROM favorites WHERE user_id=? AND product_id=?",(user["id"],pid)).fetchone()
        if existing:
            conn.execute("DELETE FROM favorites WHERE user_id=? AND product_id=?",(user["id"],pid))
            is_fav = False
        else:
            conn.execute("INSERT INTO favorites (user_id,product_id) VALUES (?,?)",(user["id"],pid))
            is_fav = True
        conn.commit(); conn.close()
    else:
        favs = session.get("favorites",[])
        if pid in favs: favs.remove(pid); is_fav = False
        else: favs.append(pid); is_fav = True
        session["favorites"] = favs
    if is_ajax:
        return jsonify({"ok": True, "is_fav": is_fav})
    return redirect(request.referrer or url_for("home"))

# ── ADMIN ─────────────────────────────────────────────────────
@app.route("/admin/products/reset", methods=["GET", "POST"])
def admin_reset_products():
    if not admin_required(): return redirect(url_for("home"))
    conn = get_db(); conn.execute("DELETE FROM products"); conn.commit(); conn.close()
    init_db()
    flash("Товары сброшены и загружены заново","success"); return redirect(url_for("admin_products"))

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
        recent_orders=recent_orders,recent_users=recent_users,theme=get_theme(),user=current_user(),lang=get_lang())

@app.route("/admin/users")
def admin_users():
    if not admin_required(): return redirect(url_for("home"))
    conn = get_db()
    users = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    stats = get_admin_stats(conn); conn.close()
    return render_template("admin.html",section="users",users=users,stats=stats,theme=get_theme(),user=current_user(),lang=get_lang())

@app.route("/admin/products")
def admin_products():
    if not admin_required(): return redirect(url_for("home"))
    conn = get_db()
    products = conn.execute("""SELECT p.*,u.username as seller_name FROM products p
        LEFT JOIN users u ON p.seller_id=u.id ORDER BY p.created_at DESC""").fetchall()
    stats = get_admin_stats(conn); conn.close()
    return render_template("admin.html",section="products",products=products,stats=stats,theme=get_theme(),user=current_user(),lang=get_lang())

@app.route("/admin/orders")
def admin_orders():
    if not admin_required(): return redirect(url_for("home"))
    conn = get_db()
    orders = conn.execute("""SELECT o.*,u.username as buyer_username FROM orders o
        LEFT JOIN users u ON o.buyer_id=u.id ORDER BY o.created_at DESC""").fetchall()
    orders_with_items = [{"order":o,"lines":conn.execute("SELECT * FROM order_items WHERE order_id=?",(o["id"],)).fetchall()} for o in orders]
    stats = get_admin_stats(conn); conn.close()
    return render_template("admin.html",section="orders",orders=orders_with_items,stats=stats,theme=get_theme(),user=current_user(),lang=get_lang())

@app.route("/admin/users/role/<int:uid>", methods=["POST"])
def admin_user_role(uid):
    if not admin_required(): return redirect(url_for("home"))
    new_role = request.form.get("role")
    if new_role in ("buyer","seller","admin"):
        conn = get_db(); conn.execute("UPDATE users SET role=? WHERE id=?",(new_role,uid)); conn.commit(); conn.close()
        flash("Роль обновлена","success")
    return redirect(url_for("admin_users"))

@app.route("/admin/users/delete/<int:uid>", methods=["POST"])
def admin_user_delete(uid):
    if not admin_required(): return redirect(url_for("home"))
    conn = get_db()
    conn.execute("DELETE FROM favorites WHERE user_id=?",(uid,))
    conn.execute("DELETE FROM products WHERE seller_id=?",(uid,))
    conn.execute("DELETE FROM users WHERE id=?",(uid,))
    conn.commit(); conn.close()
    flash("Пользователь удалён","success"); return redirect(url_for("admin_users"))

@app.route("/admin/products/delete/<int:pid>", methods=["POST"])
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
        subcategories=SUBCATEGORIES,stats=stats,theme=get_theme(),user=current_user(),lang=get_lang())

@app.route("/admin/orders/status/<int:oid>", methods=["POST"])
def admin_order_status(oid):
    if not admin_required(): return redirect(url_for("home"))
    status = request.form.get("status")
    if status in ("Новый","В обработке","Отправлен","Доставлен","Отменён"):
        conn = get_db()
        order = conn.execute("SELECT * FROM orders WHERE id=?",(oid,)).fetchone()
        conn.execute("UPDATE orders SET status=? WHERE id=?",(status,oid))
        conn.commit(); conn.close()
        flash(f"Статус заказа #{oid} обновлён на «{status}»","success")
        # Уведомляем покупателя об изменении статуса
        if order and order["email"]:
            notify_status_change(oid, order["email"], order["buyer_name"], status,
                                 address=order["address"] or "",
                                 payment=order["payment"] or "")
    return redirect(url_for("admin_orders"))

if __name__ == "__main__":
    init_db()
    conn = get_db()
    pw = generate_password_hash(ADMIN_PASSWORD)
    updated = conn.execute("UPDATE users SET password=?,role='admin' WHERE username='fureosk'",(pw,)).rowcount
    if updated == 0:
        conn.execute("""INSERT INTO users (username,email,password,role,shop_name,shop_desc)
                        VALUES ('fureosk','fureosk@shop.ru',?,'admin','Fureoska Official','Официальный магазин одежды Fureoska')""",(pw,))
    conn.commit(); conn.close()
    app.run(debug=True)

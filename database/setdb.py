import sqlite3
import datetime

# Создаем соединение с базой данных
def create_connection():
    return sqlite3.connect("database/crypto_exchange.db")

# Инициализация базы данных
def initialize_db():
    conn = create_connection()
    cursor = conn.cursor()


    # Таблица заявок
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        amount REAL NOT NULL,
        rate REAL NOT NULL,
        total REAL NOT NULL,
        status TEXT DEFAULT 'new',
        details TEXT,
        currency TEXT,
        requisites TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        operator_id INTEGER
    )
    """)


    # Таблица рефералов
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER NOT NULL,
        referred_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (referrer_id) REFERENCES users(telegram_id),
        FOREIGN KEY (referred_id) REFERENCES users(telegram_id)
    )
    """)

    # Таблица начислений реферальных бонусов
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS referral_rewards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        status TEXT DEFAULT 'pending', -- pending (ожидание), approved (подтверждено), rejected (отклонено)
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(telegram_id)
    )
    """)

    # Таблица настроек реферальной системы
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS referral_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        default_percentage REAL NOT NULL DEFAULT 5 -- Общий процент реферальных начислений
    )
    """)

    # Заполняем таблицу настроек, если она пуста
    cursor.execute("INSERT OR IGNORE INTO referral_settings (id, default_percentage) VALUES (1, 5)")

    # Таблица заявок (если её ещё нет)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        amount REAL NOT NULL,
        rate REAL NOT NULL,
        total REAL NOT NULL,
        status TEXT DEFAULT 'new',
        details TEXT,
        currency TEXT,
        requisites TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        operator_id INTEGER
    )
    """)

    # Таблица пользователей
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL UNIQUE,
        name TEXT,
        username TEXT,
        role TEXT DEFAULT 'user',
        details TEXT,
        referral_percentage REAL DEFAULT NULL -- Индивидуальный процент реферальных начислений
    )
    """)


    # Таблица криптовалют
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cryptocurrencies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name_screen TEXT,
        name TEXT NOT NULL,
        buy_rate REAL NOT NULL,
        sell_rate REAL NOT NULL,
        requisites TEXT NOT NULL,
        operator_id INTEGER
    )
    """)

    # Таблица фиатных кошельков
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fiat_wallet (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name_screen TEXT,
        details TEXT NOT NULL,
        operator_id INTEGER
    )
    """)

    # Таблица операторов
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS operators (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name_screen TEXT,
        telegram_id INTEGER NOT NULL UNIQUE,
        status TEXT DEFAULT 'active',
        work_hours TEXT DEFAULT '00:00-00:00'
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Таблица сообщений операторам
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'new',
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # Таблица логов операторов
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS operator_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        operator_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        order_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (operator_id) REFERENCES operators(id)
    )
    """)

    # Таблица для логинов и паролей операторов
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS operator_credentials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        hashed_password TEXT NOT NULL,
        operator_id INTEGER NOT NULL,
        FOREIGN KEY (operator_id) REFERENCES operators(id)
    )
    """)

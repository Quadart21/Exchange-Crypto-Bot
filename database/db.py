import sqlite3
import datetime

# Создаем соединение с базой данных
def create_connection():
    return sqlite3.connect("database/crypto_exchange.db")

# Инициализация базы данных
def initialize_db():
    create_settings_table()
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
        operator_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        uuid TEXT
                   
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
        details TEXT
    )
    """)

    # Таблица фиатных кошельков
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fiat_wallet (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name_screen TEXT,
        details TEXT NOT NULL
    )
    """)

    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS requisites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            label TEXT NOT NULL,
            details TEXT NOT NULL
        )
    """)

    
    
def get_markup_value(key):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return float(row[0]) if row else 0.0

def set_markup_value(key, value):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def create_settings_table():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('markup_percent', '0')")
    conn.commit()
    conn.close()

def get_markup_percent():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'markup_percent'")
    row = cursor.fetchone()
    conn.close()
    return float(row[0]) if row else 0.0

def update_markup_percent(value):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO settings (key, value) VALUES ('markup_percent', ?)", (str(value),))
    conn.commit()
    conn.close()

# Получение данных пользователя
def get_user_data(user_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id, name, role FROM users WHERE telegram_id = ?", (user_id,))
    data = cursor.fetchone()
    conn.close()
    return data

# Получение активных и завершенных заявок
def get_user_orders(user_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT type, amount, rate, total, status, created_at
        FROM orders
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))
    orders = cursor.fetchall()
    conn.close()
    return orders

# Подсчет оборота пользователя
def get_user_turnover(user_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT SUM(total) 
        FROM orders
        WHERE user_id = ? AND status = 'completed'
    """, (user_id,))
    turnover = cursor.fetchone()[0]
    conn.close()
    return turnover if turnover else 0


def get_requisites_by_operator(operator_id):
    """
    Получить реквизиты для заданного оператора.
    Реквизиты включают криптовалютные кошельки и фиатные реквизиты.
    """
    conn = create_connection()
    cursor = conn.cursor()
    try:
        # Получаем криптовалютные реквизиты
        cursor.execute("""
            SELECT name_screen, requisites
            FROM cryptocurrencies
            WHERE operator_id = ?
        """, (operator_id,))
        crypto_requisites = cursor.fetchall()

        # Получаем фиатные реквизиты
        cursor.execute("""
            SELECT name_screen, details
            FROM fiat_wallet
            WHERE operator_id = ?
        """, (operator_id,))
        fiat_requisites = cursor.fetchall()

        return {
            "crypto": crypto_requisites,  # Список криптовалютных реквизитов
            "fiat": fiat_requisites       # Список фиатных реквизитов
        }
    except Exception as e:
        print(f"Ошибка при получении реквизитов оператора {operator_id}: {e}")
        return {"crypto": [], "fiat": []}
    finally:
        conn.close()

import datetime


def get_operator_by_requisite(requisite_name):
    """
    Получить ID оператора, к которому привязан реквизит (криптовалюта или фиатный кошелек).
    """
    conn = create_connection()
    cursor = conn.cursor()
    try:
        # Проверка в таблице криптовалют
        cursor.execute("""
            SELECT operator_id 
            FROM cryptocurrencies
            WHERE name_screen = ? AND operator_id IS NOT NULL
        """, (requisite_name,))
        crypto_operator = cursor.fetchone()

        if crypto_operator:
            return crypto_operator[0]

        # Проверка в таблице фиатных кошельков
        cursor.execute("""
            SELECT operator_id 
            FROM fiat_wallet
            WHERE name_screen = ? AND operator_id IS NOT NULL
        """, (requisite_name,))
        fiat_operator = cursor.fetchone()

        if fiat_operator:
            return fiat_operator[0]

        return None  # Оператор не найден
    finally:
        conn.close()

def get_user_username(telegram_id):
    """Получить username пользователя по Telegram ID."""
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT details FROM users WHERE telegram_id = ?", (telegram_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        conn.close()


def update_user_username(telegram_id, username):
    """Обновить username пользователя в БД."""
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET username = ? WHERE telegram_id = ?", (username, telegram_id))
        conn.commit()
        print(f"✅ Username пользователя {telegram_id} обновлен на {username}.")
    except Exception as e:
        print(f"❌ Ошибка при обновлении username: {e}")
    finally:
        conn.close()


def get_username_by_user_id(user_id):
    """Получить username пользователя по его user_id."""
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT username FROM users WHERE telegram_id = ?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"Ошибка при получении username для user_id {user_id}: {e}")
        return None
    finally:
        conn.close()

def get_available_operators():
    """
    Получить операторов, которые работают в данный момент, игнорируя их статус.
    """
    conn = create_connection()
    cursor = conn.cursor()
    try:
        current_time = datetime.datetime.now().time()  # Текущее время
        cursor.execute("""
            SELECT id, name_screen, work_hours 
            FROM operators
        """)
        operators = cursor.fetchall()

        available_operators = []
        for operator in operators:
            operator_id, name_screen, work_hours = operator
            try:
                # Разбираем график работы
                start_time, end_time = map(
                    lambda t: datetime.datetime.strptime(t.strip(), "%H:%M").time(),
                    work_hours.split("-")
                )

                # Проверяем перекрытие суток
                if start_time <= end_time:  # Обычный интервал (в пределах одного дня)
                    if start_time <= current_time <= end_time:
                        available_operators.append((operator_id, name_screen, work_hours))
                else:  # Интервал, который перекрывает полночь
                    if current_time >= start_time or current_time <= end_time:
                        available_operators.append((operator_id, name_screen, work_hours))
            except ValueError as e:
                print(f"Ошибка в формате графика работы оператора {name_screen}: {e}")

        return available_operators
    finally:
        conn.close()

def assign_crypto_to_operator(operator_id, crypto_id):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE cryptocurrencies
            SET operator_id = ?
            WHERE id = ?
        """, (operator_id, crypto_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Ошибка при привязке криптовалюты: {e}")
        return False
    finally:
        conn.close()

def unassign_crypto_from_operator(crypto_id):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE cryptocurrencies
            SET operator_id = NULL
            WHERE id = ?
        """, (crypto_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Ошибка при отвязке криптовалюты: {e}")
        return False
    finally:
        conn.close()

def get_cryptos_by_operator(operator_id):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, name_screen
            FROM cryptocurrencies
            WHERE operator_id = ?
        """, (operator_id,))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Ошибка при получении списка криптовалют оператора: {e}")
        return []
    finally:
        conn.close()



    # Добавить правила (вставка)
def add_rules(rule_text):
    """
    Добавляет новое правило в базу данных.
    """
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO rules (rule_text) VALUES (?)", (rule_text,))
        conn.commit()
    finally:
        conn.close()

def get_rules():
    """
    Получает список всех правил из базы данных, упорядоченных по ID.
    """
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, rule_text FROM rules ORDER BY id DESC")
        rules = cursor.fetchall()  # Возвращает список кортежей (id, rule_text)
        return rules
    finally:
        conn.close()

def update_rules(new_text, rule_id):
    """
    Обновляет текст правила по его ID.
    """
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE rules SET rule_text = ? WHERE id = ?", (new_text, rule_id))
        conn.commit()
    finally:
        conn.close()

def delete_rules(rule_id):
    """
    Удаляет правило из базы данных по ID.
    """
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
        conn.commit()
    finally:
        conn.close()

def get_user_role(telegram_id):
    """
    Получает роль пользователя по его Telegram ID.
    """
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT role FROM users WHERE telegram_id = ?", (telegram_id,))
        role = cursor.fetchone()
        return role[0] if role else "user"  # Возвращает роль или "user" по умолчанию
    finally:
        conn.close()

def is_operator(telegram_id):
    """Проверяет, является ли пользователь оператором по его Telegram ID."""
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM operators WHERE telegram_id = ?", (telegram_id,))
        result = cursor.fetchone()
        return result is not None
    finally:
        conn.close()

import logging

def get_active_orders(operator_id=None):
    """
    Получает активные заявки. Если operator_id=None, возвращает все активные заявки.
    """
    conn = create_connection()
    cursor = conn.cursor()
    try:
        if operator_id is None:
            query = """
                SELECT id, user_id, type, amount, total, status, details, currency, created_at
                FROM orders
                WHERE status IN ('new', 'screenshot_uploaded', 'hash_provided')
            """
            cursor.execute(query)
        else:
            query = """
                SELECT id, user_id, type, amount, total, status, details, currency, created_at
                FROM orders
                WHERE status IN ('new', 'screenshot_uploaded', 'hash_provided') AND operator_id = ?
            """
            cursor.execute(query, (operator_id,))

        orders = cursor.fetchall()
        logging.debug(f"Найдено активных заявок: {len(orders)}")
        return orders
    finally:
        conn.close()

def fetch_order_or_raise(order_id):
    """Получить заявку по ID или поднять исключение, если заявка не найдена."""
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, user_id, type, amount, total, status, currency, details, created_at
            FROM orders
            WHERE id = ?
        """, (order_id,))
        order = cursor.fetchone()

        if not order:
            raise ValueError(f"Заявка с ID {order_id} не найдена.")

        # Возвращаем данные в виде словаря для удобства
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, order))
    finally:
        conn.close()

def delete_rules(rule_id):
    """Удаление правила по ID."""
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
        conn.commit()
    finally:
        conn.close()


def get_all_user_ids():
    """
    Получает список всех telegram_id из таблицы users.
    Возвращает список числовых значений.
    """
    conn = create_connection()  # Подключение к базе данных
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT telegram_id FROM users")
        users = [int(row[0]) for row in cursor.fetchall()]  # Преобразование в список чисел
        return users
    except Exception as e:
        print(f"Ошибка получения списка пользователей: {e}")
        return []
    finally:
        conn.close()

def get_user_id_by_username(username):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return user[0] if user else None


def get_orders_with_statuses(statuses):
    """Получить заявки с указанными статусами."""
    conn = create_connection()
    cursor = conn.cursor()
    try:
        query = f"""
            SELECT id, user_id, type, amount, currency, status
            FROM orders
            WHERE status IN ({','.join(['?' for _ in statuses])})
        """
        cursor.execute(query, statuses)
        return cursor.fetchall()  # Возвращает список кортежей
    finally:
        conn.close()


def update_order_status(order_id, status, details=None):
    """Обновить статус заявки и, при необходимости, добавить детали."""
    conn = create_connection()
    cursor = conn.cursor()
    try:
        if details:
            cursor.execute("""
                UPDATE orders 
                SET status = ?, details = ?
                WHERE id = ?
            """, (status, details, order_id))
        else:
            cursor.execute("""
                UPDATE orders 
                SET status = ?
                WHERE id = ?
            """, (status, order_id))
        conn.commit()
    finally:
        conn.close()

def get_user_id_by_order(order_id):
    """Получить user_id по ID заявки."""
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM orders WHERE id = ?", (order_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        conn.close()

def get_operator_id_by_telegram_id(telegram_id):
    """Получить operator_id по telegram_id."""
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM operators WHERE telegram_id = ?", (telegram_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        conn.close()

def get_order_by_id(order_id, is_admin=False):
    """
    Получить информацию о заявке.
    Если is_admin=True, игнорируется привязка operator_id.
    """
    conn = create_connection()
    cursor = conn.cursor()
    try:
        if is_admin:
            query = """
                SELECT id, user_id, type, amount, total, status, 
                       details, currency, requisites, operator_id, uuid
                FROM orders
                WHERE id = ?
            """
        else:
            query = """
                SELECT id, user_id, type, amount, total, status, 
                       details, currency, requisites, operator_id, uuid
                FROM orders
                WHERE id = ? AND operator_id IS NOT NULL
            """

        cursor.execute(query, (order_id,))
        order = cursor.fetchone()
        if order:
            return {
                "id": order[0], "user_id": order[1], "type": order[2],
                "amount": order[3], "total": order[4], "status": order[5],
                "details": order[6], "currency": order[7],
                "requisites": order[8], "operator_id": order[9],
                "uuid": order[10]  # <--- добавлено
            }
        return None
    finally:
        conn.close()


def update_order_status(order_id, status, operator_id=None):
    conn = create_connection()
    cursor = conn.cursor()
    if operator_id is not None:
        cursor.execute("UPDATE orders SET status = ?, operator_id = ? WHERE id = ?", (status, operator_id, order_id))
    else:
        cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()


def user_exists(telegram_id):
    """Проверка наличия пользователя в БД по Telegram ID."""
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM users WHERE telegram_id = ?", (telegram_id,))
        exists = cursor.fetchone()
        return exists is not None
    finally:
        conn.close()

def register_user(telegram_id, name, username=None):
    """Добавить нового пользователя в БД."""
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (telegram_id, name, username, role)
            VALUES (?, ?, ?, 'user')
        """, (telegram_id, name, username))
        conn.commit()
        print(f"✅ Пользователь {name} с ID {telegram_id} успешно добавлен.")
    except Exception as e:
        print(f"❌ Ошибка при добавлении пользователя: {e}")
    finally:
        conn.close()

def add_operator(telegram_id, name_screen, work_hours):
    """Добавить нового оператора в базу данных и обновить его роль на 'operator'."""
    conn = create_connection()
    cursor = conn.cursor()
    try:
        # Добавляем оператора в таблицу operators
        cursor.execute("""
            INSERT INTO operators (telegram_id, name_screen, work_hours, status)
            VALUES (?, ?, ?, 'active')
        """, (telegram_id, name_screen, work_hours))
        
        # Обновляем роль пользователя в таблице users
        cursor.execute("""
            UPDATE users 
            SET role = 'operator' 
            WHERE telegram_id = ?
        """, (telegram_id,))
        
        conn.commit()
        print(f"Оператор {name_screen} добавлен с ID {telegram_id}, роль обновлена на 'operator'.")
    except sqlite3.Error as e:
        print(f"Ошибка при добавлении оператора: {e}")
        raise
    finally:
        conn.close()



# Получить список всех операторов
def get_operators():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name_screen, telegram_id, status, work_hours FROM operators")
    operators = cursor.fetchall()
    conn.close()
    return operators

# Обновить данные оператора
def update_operator(operator_id, name_screen=None, status=None, work_hours=None):
    conn = create_connection()
    cursor = conn.cursor()
    if name_screen:
        cursor.execute("UPDATE operators SET name_screen = ? WHERE id = ?", (name_screen, operator_id))
    if status:
        cursor.execute("UPDATE operators SET status = ? WHERE id = ?", (status, operator_id))
    if work_hours:
        cursor.execute("UPDATE operators SET work_hours = ? WHERE id = ?", (work_hours, operator_id))
    conn.commit()
    conn.close()

# Удалить оператора
def delete_operator_by_telegram_id(telegram_id):
    """Удалить оператора из базы данных по его Telegram ID и изменить его роль на 'user'."""
    conn = create_connection()
    cursor = conn.cursor()
    try:
        # Проверяем, существует ли оператор с указанным telegram_id
        cursor.execute("SELECT id FROM operators WHERE telegram_id = ?", (telegram_id,))
        result = cursor.fetchone()

        if not result:
            print(f"❗ Оператор с Telegram ID {telegram_id} не найден.")
            return False  # Возвращаем False, если оператор не найден

        operator_id = result[0]

        # Удаляем оператора из таблицы operators
        cursor.execute("DELETE FROM operators WHERE id = ?", (operator_id,))
        
        # Обновляем роль в таблице users
        cursor.execute("UPDATE users SET role = 'user' WHERE telegram_id = ?", (telegram_id,))
        
        conn.commit()
        print(f"✅ Оператор с Telegram ID {telegram_id} успешно удалён, роль пользователя обновлена на 'user'.")
        return True  # Возвращаем True, если операция успешна
    except sqlite3.Error as e:
        print(f"❌ Ошибка при удалении оператора: {e}")
        return False
    finally:
        conn.close()


def get_all_requisites():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, type, label FROM requisites")
    result = cursor.fetchall()
    conn.close()
    return result

def add_requisite(rtype, label, details):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO requisites (type, label, details) VALUES (?, ?, ?)", (rtype, label, details))
    conn.commit()
    conn.close()

def delete_requisite(rid):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM requisites WHERE id = ?", (rid,))
    conn.commit()
    conn.close()

def update_requisite(rid, new_details):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE requisites SET details = ? WHERE id = ?", (new_details, rid))
    conn.commit()
    conn.close()




if __name__ == "__main__":
    initialize_db()

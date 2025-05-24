from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_ID
from database.db import get_cryptos_by_operator, get_operators, create_connection, is_operator



def get_cancel_menu():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("❌ Отмена"))

def get_main_menu(user_id, role="user"):
    print(f"Создание меню для пользователя: ID={user_id}, роль={role}, ADMIN_ID={ADMIN_ID}")

    # Проверяем, является ли пользователь администратором
    is_admin = str(user_id) in ADMIN_ID.split(',')
    print(f"Проверка на администратора: ID={user_id}, is_admin={is_admin}")

    # Проверяем, является ли пользователь оператором
    operator_status = is_operator(user_id)
    print(f"Проверка на оператора: ID={user_id}, is_operator={operator_status}")

    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add(
        KeyboardButton("💲 Купить"),
        KeyboardButton("💰 Продать"),
        KeyboardButton("👤 Профиль"),
        KeyboardButton("📜 Правила")
    )

    # Добавляем кнопки оператора и администратора
    if operator_status:  # Если пользователь найден в таблице операторов
        menu.add(KeyboardButton("Интерфейс оператора"))
    if is_admin:  # Если пользователь является администратором
        menu.add(KeyboardButton("⭐Админ-панель⭐"))

    return menu

def get_broadcast_menu():
    broadcast_menu = ReplyKeyboardMarkup(resize_keyboard=True)
    broadcast_menu.add(
        KeyboardButton("👤 Одному пользователю"),
        KeyboardButton("👥 Всем пользователям"),
        KeyboardButton("🔙 Назад")
    )
    return broadcast_menu

def get_back_menu():
    back_menu = ReplyKeyboardMarkup(resize_keyboard=True)
    back_menu.add(KeyboardButton("Назад"))
    return back_menu

# Меню оператора
def operator_menu():
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add(KeyboardButton("Активные заявки"))
    menu.add(KeyboardButton("📤 Рассылка"))
    menu.add(KeyboardButton("Назад"))
    return menu

def create_order_keyboard(order_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm:{order_id}"))
    keyboard.add(InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{order_id}"))
    return keyboard

# Клавиатура для управления операторами
def operator_management_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Показать операторов", "Добавить оператора")
    keyboard.add("Изменить данные оператора", "Удалить оператора")
    keyboard.add("Назад")
    return keyboard

# Клавиатура для редактирования оператора
def operator_edit_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Изменить имя")
    keyboard.add("Изменить рабочие часы", "Назад")
    return keyboard

def status_selection_keyboard():
    """Клавиатура для выбора статуса оператора."""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(
        KeyboardButton("🟢 Active"),
        KeyboardButton("🔴 Inactive"),
        KeyboardButton("❌ Отмена")
    )
    return keyboard
# Меню профиля
profile_menu = ReplyKeyboardMarkup(resize_keyboard=True)
profile_menu.add(
    KeyboardButton("История заявок"),
    KeyboardButton("Назад")
)

# Админ-панель
def admin_panel_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(
        KeyboardButton("Кошельки"),
        KeyboardButton("Просмотр заявок"),
        KeyboardButton("Управление правилами")
    )
    keyboard.row(
        KeyboardButton("📤 Рассылка")
    )
    keyboard.add(KeyboardButton("Выгрузить детальный отчет"))
    keyboard.add(KeyboardButton("Назад"))
    return keyboard


def get_broadcast_menu():
    broadcast_menu = ReplyKeyboardMarkup(resize_keyboard=True)
    broadcast_menu.add(
        KeyboardButton("👤 Одному пользователю"),
        KeyboardButton("👥 Всем пользователям"),
        KeyboardButton("🔙 Назад")
    )
    return broadcast_menu

def get_confirm_menu():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("Подтвердить"),
        KeyboardButton("Отмена")
    )

# Клавиатура для управления операторами
def operator_management_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Изменить статус оператора")
    keyboard.add("Показать операторов", "Добавить оператора")
    keyboard.add("Изменить данные оператора", "Удалить оператора")
    keyboard.add("Назад")
    return keyboard

# Меню управления криптовалютами
def get_crypto_menu():
    crypto_menu = ReplyKeyboardMarkup(resize_keyboard=True)
    crypto_menu.add(
        KeyboardButton("Добавить криптовалюту"),
        KeyboardButton("Список криптовалют"),
        KeyboardButton("Привязать оператора"),
        KeyboardButton("Назад в главное меню")
    )
    return crypto_menu

def get_operator_crypto_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Привязать криптовалюту"))
    keyboard.add(KeyboardButton("Отвязать криптовалюту"))
    keyboard.add(KeyboardButton("Посмотреть привязки"))
    keyboard.add(KeyboardButton("Назад в главное меню"))
    return keyboard


# Меню действий с криптовалютой
def get_crypto_action_menu():
    action_menu = ReplyKeyboardMarkup(resize_keyboard=True)
    action_menu.add(
        KeyboardButton("Изменить отображаемое имя"),
        KeyboardButton("Изменить курс покупки"),
        KeyboardButton("Изменить курс продажи"),
        KeyboardButton("Изменить реквизиты"),
        KeyboardButton("Удалить"),
        KeyboardButton("Назад в главное меню")
    )
    return action_menu


def get_crypto_keyboard():
    """Генерация клавиатуры с доступными криптовалютами для привязки."""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name_screen FROM cryptocurrencies WHERE operator_id IS NULL")  # Только непривязанные криптовалюты
    cryptos = cursor.fetchall()
    conn.close()

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for crypto in cryptos:
        keyboard.add(KeyboardButton(f"{crypto[0]}: {crypto[1]}"))  # Кнопка с ID и названием
    keyboard.add(KeyboardButton("Отмена"))  # Кнопка отмены
    return keyboard

# Меню списка криптовалют
def get_crypto_list_menu(cryptos):
    """
    Генерация меню с отображаемыми именами криптовалют.
    :param cryptos: Список криптовалют (id, name_screen).
    :return: ReplyKeyboardMarkup
    """
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for crypto in cryptos:
        keyboard.add(KeyboardButton(crypto[1]))  # Добавляем name_screen в кнопки
    keyboard.add(KeyboardButton("Назад"))  # Кнопка "Назад"
    return keyboard

# Меню управления кошельком
def get_wallet_menu():
    wallet_menu = ReplyKeyboardMarkup(resize_keyboard=True)
    wallet_menu.add(
        KeyboardButton("Добавить кошелек"),
        KeyboardButton("Изменить кошелек"),
        KeyboardButton("Удалить кошелек"),
        KeyboardButton("Назад в главное меню")
    )
    return wallet_menu

def get_operator_menu(operators):
    """Создает меню для выбора операторов."""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for operator_id, name_screen in operators:
        keyboard.add(KeyboardButton(f"ID: {operator_id} - {name_screen}"))
    keyboard.add(KeyboardButton("Отмена"))
    return keyboard

# Меню выбора кошелька на основе списка
def get_wallet_selection_menu(wallets):
    wallet_menu = ReplyKeyboardMarkup(resize_keyboard=True)

    if not wallets:
        wallet_menu.add(KeyboardButton("Список пуст"))
        wallet_menu.add(KeyboardButton("В главное меню"))
        return wallet_menu

    for wallet in wallets:
        try:
            clean_details = wallet[1].replace('\n', ' ').strip()[:50]  # Очистка и обрезка
            wallet_menu.add(KeyboardButton(f"ID: {wallet[0]} - {clean_details}"))
        except Exception as e:
            print(f"Ошибка при добавлении кнопки: ID={wallet[0]}, Details={wallet[1]}. Ошибка: {e}")

    wallet_menu.add(KeyboardButton("Назад"))
    return wallet_menu

def add_main_menu_button(keyboard: ReplyKeyboardMarkup) -> ReplyKeyboardMarkup:
    """
    Добавляет кнопку 'В главное меню' к указанной клавиатуре, если она ещё не добавлена.
    
    :param keyboard: Исходная клавиатура.
    :return: Клавиатура с добавленной кнопкой.
    """
    # Проверяем, есть ли кнопка "В главное меню"
    for row in keyboard.keyboard:
        for button in row:
            if button.text == "В главное меню":
                return keyboard  # Кнопка уже есть, ничего не добавляем
    keyboard.add(KeyboardButton("В главное меню"))  # Добавляем кнопку
    return keyboard

# Меню выбора валюты
def currency_keyboard(currencies):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for currency in currencies:
        keyboard.add(KeyboardButton(currency))
    keyboard.add(KeyboardButton("В главное меню"))
    return keyboard


def get_operator_keyboard():
    """Генерация клавиатуры с операторами."""
    operators = get_operators()
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    
    for operator in operators:
        keyboard.add(KeyboardButton(f"{operator[0]}: {operator[1]}"))  # Формат кнопки: "ID: Имя"
    keyboard.add(KeyboardButton("Отмена"))  # Кнопка отмены
    return keyboard

def get_crypto_unassign_keyboard(operator_id):
    """Генерация клавиатуры с привязанными криптовалютами для отвязки."""
    cryptos = get_cryptos_by_operator(operator_id)  # Получаем привязанные криптовалюты
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

    if not cryptos:
        keyboard.add(KeyboardButton("Нет привязанных криптовалют"))
        keyboard.add(KeyboardButton("Отмена"))
        return keyboard

    for crypto in cryptos:
        keyboard.add(KeyboardButton(f"{crypto[0]}: {crypto[1]}"))  # Формат кнопки: "ID: Название"
    keyboard.add(KeyboardButton("Отмена"))  # Кнопка отмены
    return keyboard

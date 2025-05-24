from aiogram import Dispatcher, types
from database.db import create_connection

# Функция для получения текста правил
def get_rules():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT text FROM rules ORDER BY id DESC LIMIT 1")
    rule = cursor.fetchone()
    conn.close()
    return rule[0] if rule else "Правила не установлены."

# Обработчик для отправки правил пользователю
async def send_rules(message: types.Message):
    rules_text = get_rules()
    await message.answer(rules_text)

# Регистрация обработчиков для пользователей
def register_user_rules_handlers(dp: Dispatcher):
    dp.register_message_handler(send_rules, text="Правила")

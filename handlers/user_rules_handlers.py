from aiogram import types
from database.db import get_rules
from config import dp

# Функция форматирования правил
def format_rules(rules):
    if not rules:
        return "Правила отсутствуют."
    formatted = "Текущие правила:\n\n"
    for rule_id, rule_text in rules:
        formatted += f"{rule_text}\n\n"
    return formatted.strip()

# Пользователь: просмотр правил
@dp.message_handler(lambda message: message.text == "📜 Правила")
async def view_rules_handler(message: types.Message):
    rules = get_rules()
    formatted_rules = format_rules(rules)
    await message.reply(formatted_rules, parse_mode="HTML")

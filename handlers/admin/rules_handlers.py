from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher.filters.state import State, StatesGroup
from database.db import add_rules, get_rules, update_rules, delete_rules, get_user_role
from config import dp  # Убедитесь, что здесь загружается диспетчер из вашего проекта

# Состояния для работы с правилами
class RuleManagement(StatesGroup):
    adding = State()
    editing = State()
    deleting = State()

# Клавиатура управления правилами
def rules_menu():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("Просмотреть правила"),
        KeyboardButton("Добавить правило"),
        KeyboardButton("Редактировать правило"),
        KeyboardButton("Удалить правило"),
        KeyboardButton("Назад")
    )

# Обработчик для входа в меню управления правилами
@dp.message_handler(Text(equals="Управление правилами"))
async def manage_rules(message: types.Message):
    await message.answer("Выберите действие:", reply_markup=rules_menu())

# Обработчик для просмотра правил
@dp.message_handler(Text(equals="Просмотреть правила"))
async def view_rules(message: types.Message):
    rules = get_rules()
    confirmation_message = "Текущие правила:\n\n"
    if rules:
        for rule_id, rule_text in rules:
            confirmation_message += f"ID: {rule_id}\n{rule_text}\n\n"
    else:
        confirmation_message += "Правила отсутствуют."
    await message.answer(confirmation_message, reply_markup=rules_menu())

# Обработчик для добавления правила
@dp.message_handler(Text(equals="Добавить правило"))
async def start_adding_rule(message: types.Message):
    await message.answer("Введите текст нового правила:")
    await RuleManagement.adding.set()

@dp.message_handler(state=RuleManagement.adding)
async def add_rule(message: types.Message, state: FSMContext):
    add_rules(message.text)
    await message.answer(f"Новое правило добавлено:\n\n{message.text}", reply_markup=rules_menu())
    await state.finish()

@dp.message_handler(Text(equals="Редактировать правило"))
async def start_editing_rule(message: types.Message):
    rules = get_rules()
    edit_message = "Текущие правила:\n\n"
    if rules:
        for rule_id, rule_text in rules:
            edit_message += f"ID: {rule_id}\n{rule_text}\n\n"
    else:
        edit_message += "Правила отсутствуют."
    await message.answer(edit_message + "Введите ID правила для редактирования и новый текст через \":\" (Пример: 1:Новый текст):")
    await RuleManagement.editing.set()

@dp.message_handler(state=RuleManagement.editing)
async def edit_rule(message: types.Message, state: FSMContext):
    try:
        rule_id, new_text = message.text.split(":", 1)
        update_rules(new_text, int(rule_id))
        await message.answer(f"Правило с ID {rule_id} обновлено:\n\n{new_text}", reply_markup=rules_menu())
    except ValueError:
        await message.answer("Введите корректный формат ID и текста!")
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")
    await state.finish()

# Обработчик для удаления правила
@dp.message_handler(Text(equals="Удалить правило"))
async def start_deleting_rule(message: types.Message):
    rules = get_rules()
    delete_message = "Текущие правила:\n\n"
    if rules:
        for rule_id, rule_text in rules:
            delete_message += f"ID: {rule_id}\n{rule_text}\n\n"
    else:
        delete_message += "Правила отсутствуют."
    await message.answer(delete_message + "Введите ID правила для удаления:")
    await RuleManagement.deleting.set()

@dp.message_handler(state=RuleManagement.deleting)
async def delete_rule(message: types.Message, state: FSMContext):
    try:
        rule_id = int(message.text)
        delete_rules(rule_id)
        await message.answer(f"Правило с ID {rule_id} удалено.", reply_markup=rules_menu())
    except ValueError:
        await message.answer("Введите корректный ID!")
    except Exception as e:
        await message.answer(f"Произошла ошибка при удалении: {str(e)}")
    await state.finish()

# Добавление логики возврата в главное меню администратора
@dp.message_handler(Text(equals="Назад"))
async def go_back_to_admin_menu(message: types.Message):
    await message.answer("Возврат в главное меню администратора.", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("Управление правилами"),
        KeyboardButton("Другие функции")
    ))

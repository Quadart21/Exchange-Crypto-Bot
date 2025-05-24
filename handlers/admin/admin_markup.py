from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from config import dp
from database.db import get_user_role, set_markup_value
from keyboards.main_menu import admin_panel_menu



class MarkupFSM(StatesGroup):
    choosing_type = State()
    entering_value = State()


# Человеческие названия и ключи в БД
markup_keys = {
    "Купить USDT/USDC": "markup_buy_usd",
    "Купить другие": "markup_buy_other",
    "Продать USDT/USDC": "markup_sell_usd",
    "Продать другие": "markup_sell_other"
}

@dp.message_handler(lambda message: message.text in ["Изменить наценку", "Изменить Процент"])
async def markup_start(msg: types.Message):
    print(f"[DEBUG] Получено сообщение: {msg.text} от ID {msg.from_user.id}")
    
    if get_user_role(msg.from_user.id) != 'admin':
        print("[DEBUG] Пользователь не админ. Прерываем.")
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for label in markup_keys:
        kb.add(types.KeyboardButton(label))
    kb.add(types.KeyboardButton("🔙 Назад"))

    print("[DEBUG] Показываем меню наценок")
    await msg.answer("Выберите категорию:", reply_markup=kb)
    await MarkupFSM.choosing_type.set()

# Выбор типа
@dp.message_handler(lambda m: m.text in markup_keys, state=MarkupFSM.choosing_type)
async def choose_type(msg: types.Message, state: FSMContext):
    await state.update_data(key=markup_keys[msg.text])
    await msg.answer(f"Введите процент (можно с минусом) для «{msg.text}»:")
    await MarkupFSM.entering_value.set()

# Ввод значения
@dp.message_handler(state=MarkupFSM.entering_value)
async def enter_value(msg: types.Message, state: FSMContext):
    try:
        value = float(msg.text.replace(",", "."))
    except:
        return await msg.answer("⚠ Введите число, например: -3 или 5.5")

    data = await state.get_data()
    set_markup_value(data["key"], value)
    await msg.answer(f"✅ Установлено: {value}%")
    await state.finish()

# Назад в админ-панель
@dp.message_handler(Text(equals="🔙 Назад"), state="*")
async def back_to_admin_panel(msg: types.Message, state: FSMContext):
    await state.finish()
    await msg.answer("🔧 Возврат в админ-панель", reply_markup=admin_panel_menu())

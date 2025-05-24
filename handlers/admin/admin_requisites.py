# handlers/admin_requisites.py
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from config import dp
from database.db import get_all_requisites, add_requisite, delete_requisite, update_requisite
from keyboards.main_menu import get_back_menu, admin_panel_menu
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

class RequisiteFSM(StatesGroup):
    type = State()
    label = State()
    details = State()
    choose_id_to_edit = State()
    new_details = State()
    choose_id_to_delete = State()


@dp.message_handler(lambda msg: msg.text in ["Главное меню", "🔙 Назад", "Назад"])
async def to_admin_menu(msg: types.Message, state: FSMContext):
    await state.finish()
    await msg.answer("Главное меню:", reply_markup=admin_panel_menu())

# Главное меню реквизитов
@dp.message_handler(lambda msg: msg.text == "Кошельки")
async def requisites_menu(message: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Добавить реквизит", "📝 Изменить реквизит")
    kb.add("❌ Удалить реквизит", "Главное меню")
    await message.answer("Выберите действие:", reply_markup=kb)

# Добавить
@dp.message_handler(lambda msg: msg.text == "➕ Добавить реквизит")
async def add_req_start(message: types.Message):
    await RequisiteFSM.type.set()
    await message.answer("Введите тип (fiat / crypto):", reply_markup=get_back_menu())

@dp.message_handler(state=RequisiteFSM.type)
async def add_req_type(message: types.Message, state: FSMContext):
    await state.update_data(type=message.text)
    await RequisiteFSM.label.set()
    await message.answer("Введите название реквизита:")

@dp.message_handler(state=RequisiteFSM.label)
async def add_req_label(message: types.Message, state: FSMContext):
    await state.update_data(label=message.text)
    await RequisiteFSM.details.set()
    await message.answer("Введите содержимое реквизита:")

@dp.message_handler(state=RequisiteFSM.details)
async def add_req_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    add_requisite(data["type"], data["label"], message.text)
    await state.finish()
    await message.answer("✅ Реквизит добавлен.")

# Изменить
@dp.message_handler(lambda msg: msg.text == "📝 Изменить реквизит")
async def edit_req_list(message: types.Message):
    reqs = get_all_requisites()
    if not reqs:
        return await message.answer("Нет реквизитов.")
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for r in reqs:
        kb.add(f"{r[0]} | {r[1]} | {r[2]}")
    kb.add("Главное меню")
    await message.answer("Выберите реквизит по ID:", reply_markup=kb)
    await RequisiteFSM.choose_id_to_edit.set()

@dp.message_handler(state=RequisiteFSM.choose_id_to_edit)
async def edit_req_enter(message: types.Message, state: FSMContext):
    rid = message.text.split()[0]
    await state.update_data(edit_id=int(rid))
    await RequisiteFSM.new_details.set()
    await message.answer("Введите новые реквизиты:")

@dp.message_handler(state=RequisiteFSM.new_details)
async def edit_req_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    update_requisite(data["edit_id"], message.text)
    await state.finish()
    await message.answer("✅ Реквизит обновлён.")

# Удалить
@dp.message_handler(lambda msg: msg.text == "❌ Удалить реквизит")
async def delete_req_list(message: types.Message):
    reqs = get_all_requisites()
    if not reqs:
        return await message.answer("Нет реквизитов.")
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for r in reqs:
        kb.add(f"{r[0]} | {r[1]} | {r[2]}")
    kb.add("🔙 Назад")
    await message.answer("Выберите ID для удаления:", reply_markup=kb)
    await RequisiteFSM.choose_id_to_delete.set()

@dp.message_handler(state=RequisiteFSM.choose_id_to_delete)
async def delete_req_confirm(message: types.Message, state: FSMContext):
    rid = message.text.split()[0]
    delete_requisite(int(rid))
    await state.finish()
    await message.answer("✅ Реквизит удалён.")

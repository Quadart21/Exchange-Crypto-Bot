from aiogram import types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from config import dp
from database.db import create_connection
from keyboards.main_menu import admin_panel_menu, get_operator_menu, get_wallet_selection_menu

class FiatWalletState(StatesGroup):
    choosing_action = State()
    adding_wallet = State()
    editing_wallet = State()
    updating_wallet = State()
    updating_name_screen = State()
    deleting_wallet = State()
    assigning_operator = State()
    viewing_wallets = State()
    choosing_operator = State()

@dp.message_handler(lambda message: message.text == "Управление фиатом", state="*")
async def manage_fiat_wallet(message: types.Message):
    wallet_menu = ReplyKeyboardMarkup(resize_keyboard=True)
    wallet_menu.add("Просмотр кошельков", "Добавить кошелек")
    wallet_menu.add("Изменить кошелек", "Удалить кошелек")
    wallet_menu.add("Привязать кошелек к оператору")
    wallet_menu.add("Назад")
    await message.answer("Выберите действие с фиатным кошельком:", reply_markup=wallet_menu)
    await FiatWalletState.choosing_action.set()

@dp.message_handler(lambda message: message.text == "Просмотр кошельков", state=FiatWalletState.choosing_action)
async def view_fiat_wallets(message: types.Message, state: FSMContext):
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT f.id, f.name_screen, f.details, o.name_screen FROM fiat_wallet f LEFT JOIN operators o ON f.operator_id = o.id")
        wallets = cursor.fetchall()

    if not wallets:
        await message.answer("Список кошельков пуст.", reply_markup=admin_panel_menu())
        await state.finish()
        return

    response = "Список фиатных кошельков:\n"
    for wallet in wallets:
        response += f"\nID: {wallet[0]}\nИмя: {wallet[1]}\nДетали: {wallet[2]}\nПривязан к оператору: {wallet[3] or 'Не привязан'}\n"

    await message.answer(response, reply_markup=admin_panel_menu())
    await state.finish()

@dp.message_handler(lambda message: message.text == "Привязать кошелек к оператору", state=FiatWalletState.choosing_action)
async def assign_wallet_to_operator_start(message: types.Message, state: FSMContext):
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name_screen FROM fiat_wallet")
        wallets = cursor.fetchall()

    if not wallets:
        await message.answer("Нет доступных кошельков для привязки.", reply_markup=admin_panel_menu())
        await state.finish()
        return

    wallet_menu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for wallet in wallets:
        wallet_menu.add(KeyboardButton(f"ID: {wallet[0]} - {wallet[1]}"))
    wallet_menu.add(KeyboardButton("Назад"))

    await message.answer("Выберите кошелек для привязки к оператору:", reply_markup=wallet_menu)
    await FiatWalletState.assigning_operator.set()

@dp.message_handler(state=FiatWalletState.assigning_operator, content_types=types.ContentTypes.TEXT)
async def assign_wallet_to_operator(message: types.Message, state: FSMContext):
    try:
        if message.text == "Назад":
            await manage_fiat_wallet(message)
            return

        wallet_id = int(message.text.split("ID: ")[1].split(" - ")[0])
        await state.update_data(wallet_id=wallet_id)

        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name_screen FROM operators")
            operators = cursor.fetchall()

        if not operators:
            await message.answer("Нет доступных операторов.", reply_markup=admin_panel_menu())
            await state.finish()
            return

        operator_menu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for operator in operators:
            operator_menu.add(KeyboardButton(f"ID: {operator[0]} - {operator[1]}"))
        operator_menu.add(KeyboardButton("Назад"))

        await message.answer("Выберите оператора для привязки:", reply_markup=operator_menu)
        await FiatWalletState.choosing_operator.set()
    except (ValueError, IndexError):
        await message.answer("Пожалуйста, выберите корректный ID кошелька.")

@dp.message_handler(state=FiatWalletState.choosing_operator, content_types=types.ContentTypes.TEXT)
async def confirm_wallet_assignment(message: types.Message, state: FSMContext):
    try:
        if message.text == "Назад":
            await manage_fiat_wallet(message)
            return

        operator_id = int(message.text.split("ID: ")[1].split(" - ")[0])
        data = await state.get_data()
        wallet_id = data["wallet_id"]

        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE fiat_wallet SET operator_id = ? WHERE id = ?", (operator_id, wallet_id))
            conn.commit()

        await message.answer("Кошелек успешно привязан к оператору.", reply_markup=admin_panel_menu())
        await state.finish()
    except (ValueError, IndexError):
        await message.answer("Пожалуйста, выберите корректный ID оператора.")

@dp.message_handler(lambda message: message.text == "Добавить кошелек", state=FiatWalletState.choosing_action)
async def add_fiat_wallet(message: types.Message):
    await message.answer("Введите реквизиты нового кошелька:")
    await FiatWalletState.adding_wallet.set()

@dp.message_handler(state=FiatWalletState.adding_wallet, content_types=types.ContentTypes.TEXT)
async def save_fiat_wallet(message: types.Message, state: FSMContext):
    wallet_details = message.text.strip()
    await state.update_data(wallet_details=wallet_details)
    await message.answer("Введите имя для отображения (name screen) кошелька:")
    await FiatWalletState.updating_name_screen.set()

@dp.message_handler(state=FiatWalletState.updating_name_screen, content_types=types.ContentTypes.TEXT)
async def save_name_screen(message: types.Message, state: FSMContext):
    data = await state.get_data()
    wallet_details = data["wallet_details"]
    name_screen = message.text.strip()

    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO fiat_wallet (details, name_screen) VALUES (?, ?)", (wallet_details, name_screen))
        conn.commit()

    await message.answer("Кошелек успешно добавлен с именем для отображения.", reply_markup=admin_panel_menu())
    await state.finish()

@dp.message_handler(lambda message: message.text == "Изменить кошелек", state=FiatWalletState.choosing_action)
async def edit_fiat_wallet_start(message: types.Message, state: FSMContext):
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name_screen, details FROM fiat_wallet")
        wallets = cursor.fetchall()

    if not wallets:
        await message.answer("Список кошельков пуст.", reply_markup=admin_panel_menu())
        await state.finish()
        return

    wallet_menu = get_wallet_selection_menu([(wallet[0], wallet[1]) for wallet in wallets])
    await message.answer("Выберите кошелек для редактирования:", reply_markup=wallet_menu)
    await FiatWalletState.editing_wallet.set()

@dp.message_handler(state=FiatWalletState.editing_wallet, content_types=types.ContentTypes.TEXT)
async def edit_fiat_wallet(message: types.Message, state: FSMContext):
    try:
        wallet_id = int(message.text.split("ID: ")[1].split(" - ")[0])
        await state.update_data(wallet_id=wallet_id)
        await message.answer("Введите новые реквизиты для кошелька:")
        await FiatWalletState.updating_wallet.set()
    except (ValueError, IndexError):
        await message.answer("Пожалуйста, выберите корректный ID кошелька.")

@dp.message_handler(state=FiatWalletState.updating_wallet, content_types=types.ContentTypes.TEXT)
async def update_fiat_wallet(message: types.Message, state: FSMContext):
    data = await state.get_data()
    wallet_id = data["wallet_id"]
    new_details = message.text.strip()

    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE fiat_wallet SET details = ? WHERE id = ?", (new_details, wallet_id))
        conn.commit()

    await message.answer("Реквизиты кошелька успешно обновлены.", reply_markup=admin_panel_menu())
    await state.finish()

@dp.message_handler(lambda message: message.text == "Удалить кошелек", state=FiatWalletState.choosing_action)
async def delete_fiat_wallet(message: types.Message, state: FSMContext):
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name_screen, details FROM fiat_wallet")
        wallets = cursor.fetchall()

    if not wallets:
        await message.answer("Нет доступных кошельков для удаления.", reply_markup=admin_panel_menu())
        await state.finish()
        return

    wallet_menu = get_wallet_selection_menu([(wallet[0], wallet[1]) for wallet in wallets])
    await message.answer("Выберите кошелек для удаления:", reply_markup=wallet_menu)
    await FiatWalletState.deleting_wallet.set()

@dp.message_handler(state=FiatWalletState.deleting_wallet, content_types=types.ContentTypes.TEXT)
async def delete_wallet_confirm(message: types.Message, state: FSMContext):
    try:
        wallet_id = int(message.text.split("ID: ")[1].split(" - ")[0])
        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM fiat_wallet WHERE id = ?", (wallet_id,))
            conn.commit()

        await message.answer("Кошелек успешно удален.", reply_markup=admin_panel_menu())
        await state.finish()
    except (ValueError, IndexError):
        await message.answer("Пожалуйста, выберите корректный ID кошелька.")

@dp.message_handler(lambda message: message.text == "Привязать кошелек к оператору", state=FiatWalletState.choosing_action)
async def assign_wallet_to_operator_start(message: types.Message, state: FSMContext):
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name_screen, details FROM fiat_wallet")
        wallets = cursor.fetchall()

    if not wallets:
        await message.answer("Нет доступных кошельков для привязки.", reply_markup=admin_panel_menu())
        await state.finish()
        return

    wallet_menu = get_wallet_selection_menu([(wallet[0], wallet[1]) for wallet in wallets])
    await message.answer("Выберите кошелек для привязки к оператору:", reply_markup=wallet_menu)
    await FiatWalletState.assigning_operator.set()

@dp.message_handler(state=FiatWalletState.assigning_operator, content_types=types.ContentTypes.TEXT)
async def assign_wallet_to_operator(message: types.Message, state: FSMContext):
    try:
        wallet_id = int(message.text.split("ID: ")[1].split(" - ")[0])
        await state.update_data(wallet_id=wallet_id)

        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name_screen FROM operators")
            operators = cursor.fetchall()

        if not operators:
            await message.answer("Нет доступных операторов.", reply_markup=admin_panel_menu())
            await state.finish()
            return

        operator_menu = get_operator_menu([(operator[0], operator[1]) for operator in operators])
        await message.answer("Выберите оператора для привязки:", reply_markup=operator_menu)
    except (ValueError, IndexError):
        await message.answer("Пожалуйста, выберите корректный ID кошелька.")

@dp.message_handler(state=FiatWalletState.assigning_operator, content_types=types.ContentTypes.TEXT)
async def confirm_wallet_assignment(message: types.Message, state: FSMContext):
    try:
        operator_id = int(message.text.split("ID: ")[1].split(" - ")[0])
        data = await state.get_data()
        wallet_id = data["wallet_id"]

        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE fiat_wallet SET operator_id = ? WHERE id = ?", (operator_id, wallet_id))
            conn.commit()

        await message.answer("Кошелек успешно привязан к оператору.", reply_markup=admin_panel_menu())
        await state.finish()
    except (ValueError, IndexError):
        await message.answer("Пожалуйста, выберите корректный ID оператора.")

from aiogram import types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from config import dp, ADMIN_ID
from keyboards.main_menu import admin_panel_menu, get_crypto_action_menu, get_main_menu, get_crypto_list_menu, get_crypto_menu
from aiogram import types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from database.db import create_connection
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

class CryptoState(StatesGroup):
    waiting_for_screen_name = State()
    waiting_for_name = State()
    waiting_for_buy_rate = State()
    waiting_for_sell_rate = State()
    waiting_for_requisites = State()
    choosing_crypto = State()
    editing_crypto = State()
    changing_screen_name = State()
    changing_buy_rate = State()
    changing_sell_rate = State()
    changing_requisites = State()


# Универсальная обработка кнопки "Назад"
@dp.message_handler(lambda message: message.text == "Назад в главное меню", state="*")
async def go_back(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.finish()  # Завершаем текущее состояние
    
    # Проверяем, является ли пользователь администратором
    if str(message.from_user.id) in ADMIN_ID.split(','):
        # Для админов возвращаем админ-панель
        await message.answer("Возвращаемся в админ-панель.", reply_markup=admin_panel_menu())
    else:
        # Для обычных пользователей возвращаем главное меню
        await message.answer("Возвращаемся в главное меню.", reply_markup=get_main_menu)

# Команда для входа в админ-меню
@dp.message_handler(lambda message: message.text == "⭐Админ-панель⭐")
async def admin_panel(message: types.Message):
    if str(message.from_user.id) not in ADMIN_ID.split(','):
        await message.answer("У вас нет доступа к этой функции.")
        return

    # Используем обновленное меню с кнопкой "Управление кошельком"
    await message.answer(
        "Добро пожаловать в админ-панель. Выберите действие:",
        reply_markup=admin_panel_menu()
    )

@dp.message_handler(lambda message: message.text == "Управление криптовалютами")
async def manage_cryptos(message: types.Message):
    # Отправляем сообщение с меню управления криптовалютами
    await message.answer("Выберите действие:", reply_markup=get_crypto_menu())

# Добавление криптовалюты
@dp.message_handler(lambda message: message.text == "Добавить криптовалюту")
async def add_crypto_start(message: types.Message):
    if message.text == "Назад":
        await go_back(message, None)
        return
    await message.answer("Введите отображаемое название криптовалюты:")
    await CryptoState.waiting_for_screen_name.set()

@dp.message_handler(state=CryptoState.waiting_for_screen_name, content_types=types.ContentTypes.TEXT)
async def add_crypto_screen_name(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await go_back(message, state)
        return
    await state.update_data(name_screen=message.text)
    await message.answer("Введите название криптовалюты (системное имя):")
    await CryptoState.waiting_for_name.set()

@dp.message_handler(state=CryptoState.waiting_for_name, content_types=types.ContentTypes.TEXT)
async def add_crypto_name(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await go_back(message, state)
        return
    await state.update_data(name=message.text)
    await message.answer("Введите курс покупки:")
    await CryptoState.waiting_for_buy_rate.set()

@dp.message_handler(state=CryptoState.waiting_for_buy_rate, content_types=types.ContentTypes.TEXT)
async def add_crypto_buy_rate(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await go_back(message, state)
        return
    try:
        buy_rate = float(message.text)
        await state.update_data(buy_rate=buy_rate)
        await message.answer("Введите курс продажи:")
        await CryptoState.waiting_for_sell_rate.set()
    except ValueError:
        await message.answer("Пожалуйста, введите корректное числовое значение для курса покупки.")

@dp.message_handler(state=CryptoState.waiting_for_sell_rate, content_types=types.ContentTypes.TEXT)
async def add_crypto_sell_rate(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await go_back(message, state)
        return
    try:
        sell_rate = float(message.text)
        await state.update_data(sell_rate=sell_rate)
        await message.answer("Введите реквизиты:")
        await CryptoState.waiting_for_requisites.set()
    except ValueError:
        await message.answer("Пожалуйста, введите корректное числовое значение для курса продажи.")

@dp.message_handler(state=CryptoState.waiting_for_requisites, content_types=types.ContentTypes.TEXT)
async def add_crypto_requisites(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await message.answer("Возвращаюсь в меню управления криптовалютами.", reply_markup=get_crypto_menu())
        await state.finish()
        return

    # Получаем данные из состояния
    data = await state.get_data()
    name_screen = data.get('name_screen')
    name = data.get('name')
    buy_rate = data.get('buy_rate')
    sell_rate = data.get('sell_rate')
    requisites = message.text

    try:
        # Записываем данные в базу
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO cryptocurrencies (name_screen, name, buy_rate, sell_rate, requisites) VALUES (?, ?, ?, ?, ?)",
            (name_screen, name, float(buy_rate), float(sell_rate), requisites)
        )
        conn.commit()
        conn.close()

        # Сообщаем об успешном добавлении
        await message.answer(f"Криптовалюта '{name_screen}' успешно добавлена!", reply_markup=get_crypto_menu())
        await state.finish()
    except Exception as e:
        await message.answer("Произошла ошибка при добавлении криптовалюты. Пожалуйста, попробуйте снова.")
        print(f"Error: {e}")  # Логируем ошибку в консоль
        await state.finish()



# Список криптовалют
@dp.message_handler(lambda message: message.text == "Список криптовалют")
async def list_cryptos(message: types.Message):
    if message.text == "Назад":
        await go_back(message, None)
        return

    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name_screen FROM cryptocurrencies")
    cryptos = cursor.fetchall()
    conn.close()

    if not cryptos:
        await message.answer("Криптовалюты не найдены.")
        return

    # Использование новой клавиатуры с отображаемыми именами
    crypto_list_menu = get_crypto_list_menu(cryptos)
    await message.answer("Выберите криптовалюту для управления:", reply_markup=crypto_list_menu)
    await CryptoState.choosing_crypto.set()

@dp.message_handler(state=CryptoState.choosing_crypto, content_types=types.ContentTypes.TEXT)
async def choose_crypto(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await go_back(message, state)
        return

    crypto_name = message.text
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name_screen, name, buy_rate, sell_rate, requisites FROM cryptocurrencies WHERE name_screen = ?", (crypto_name,))
    crypto = cursor.fetchone()
    conn.close()

    if not crypto:
        await message.answer("Криптовалюта не найдена.")
        return

    await state.update_data(crypto_id=crypto[0])

    # Использование клавиатуры действий с криптовалютой
    action_menu = get_crypto_action_menu()
    await message.answer(
        f"Криптовалюта: {crypto[1]}\n(Системное имя: {crypto[2]})\nПокупка: {crypto[3]}\nПродажа: {crypto[4]}\nРеквизиты: {crypto[5]}\n\nВыберите действие:",
        reply_markup=action_menu
    )
    await CryptoState.editing_crypto.set()

@dp.message_handler(state=CryptoState.editing_crypto, content_types=types.ContentTypes.TEXT)
async def edit_or_delete_crypto(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await go_back(message, state)
        return

    action = message.text
    data = await state.get_data()
    crypto_id = data['crypto_id']

    if action == "Изменить отображаемое имя":
        await message.answer("Введите новое отображаемое имя:")
        await CryptoState.changing_screen_name.set()
    elif action == "Изменить курс покупки":
        await message.answer("Введите новый курс покупки:")
        await CryptoState.changing_buy_rate.set()
    elif action == "Изменить курс продажи":
        await message.answer("Введите новый курс продажи:")
        await CryptoState.changing_sell_rate.set()
    elif action == "Изменить реквизиты":
        await message.answer("Введите новые реквизиты:")
        await CryptoState.changing_requisites.set()
    elif action == "Удалить":
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cryptocurrencies WHERE id = ?", (crypto_id,))
        conn.commit()
        conn.close()

        await message.answer("Криптовалюта успешно удалена.", reply_markup=crypto_menu)
        await state.finish()
    else:
        await message.answer("Некорректный выбор. Пожалуйста, выберите действие.")

@dp.message_handler(state=CryptoState.changing_screen_name, content_types=types.ContentTypes.TEXT)
async def change_screen_name(message: types.Message, state: FSMContext):
    new_screen_name = message.text
    if new_screen_name == "Назад":
        await go_back(message, state)
        return

    data = await state.get_data()
    crypto_id = data['crypto_id']

    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE cryptocurrencies SET name_screen = ? WHERE id = ?", (new_screen_name, crypto_id))
        conn.commit()
        await message.answer(f"Отображаемое имя успешно изменено на '{new_screen_name}'.", reply_markup=get_crypto_action_menu())
        await CryptoState.editing_crypto.set()
    except Exception as e:
        await message.answer("Произошла ошибка при обновлении отображаемого имени. Пожалуйста, попробуйте снова.")
        print(f"Error: {e}")
    finally:
        conn.close()



# Хэндлер для обновления курса покупки
@dp.message_handler(lambda message: message.text == "Изменить курс покупки", state="*")
async def change_buy_rate_prompt(message: types.Message, state: FSMContext):
    await message.answer("Введите новый курс покупки для выбранной криптовалюты или нажмите 'Назад'.",
                         reply_markup=get_crypto_menu())  # Меню управления криптовалютами
    await CryptoState.changing_buy_rate.set()

@dp.message_handler(state=CryptoState.changing_buy_rate, content_types=types.ContentTypes.TEXT)
async def change_buy_rate(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await message.answer("Возвращаюсь в меню управления криптовалютами.", reply_markup=get_crypto_menu())
        await state.finish()
        return
    try:
        new_rate = float(message.text)
        data = await state.get_data()
        crypto_id = data['crypto_id']

        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE cryptocurrencies SET buy_rate = ? WHERE id = ?", (new_rate, crypto_id))
        conn.commit()
        conn.close()

        await message.answer("Курс покупки успешно обновлен.", reply_markup=get_crypto_menu())
        await state.finish()
    except ValueError:
        await message.answer("Пожалуйста, введите корректное числовое значение.")

# Хэндлер для обновления курса продажи
@dp.message_handler(lambda message: message.text == "Изменить курс продажи", state="*")
async def change_sell_rate_prompt(message: types.Message, state: FSMContext):
    await message.answer("Введите новый курс продажи для выбранной криптовалюты или нажмите 'Назад'.",
                         reply_markup=get_crypto_menu())
    await CryptoState.changing_sell_rate.set()

@dp.message_handler(state=CryptoState.changing_sell_rate, content_types=types.ContentTypes.TEXT)
async def change_sell_rate(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await message.answer("Возвращаюсь в меню управления криптовалютами.", reply_markup=get_crypto_menu())
        await state.finish()
        return
    try:
        new_rate = float(message.text)
        data = await state.get_data()
        crypto_id = data['crypto_id']

        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE cryptocurrencies SET sell_rate = ? WHERE id = ?", (new_rate, crypto_id))
        conn.commit()
        conn.close()

        await message.answer("Курс продажи успешно обновлен.", reply_markup=get_crypto_menu())
        await state.finish()
    except ValueError:
        await message.answer("Пожалуйста, введите корректное числовое значение.")

# Хэндлер для редактирования реквизитов
@dp.message_handler(lambda message: message.text == "Редактировать реквизиты", state="*")
async def change_requisites_prompt(message: types.Message, state: FSMContext):
    await message.answer("Введите новые реквизиты для криптовалюты или нажмите 'Назад'.",
                         reply_markup=get_crypto_menu())
    await CryptoState.changing_requisites.set()

@dp.message_handler(state=CryptoState.changing_requisites, content_types=types.ContentTypes.TEXT)
async def change_requisites(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await message.answer("Возвращаюсь в меню управления криптовалютами.", reply_markup=get_crypto_menu())
        await state.finish()
        return
    new_requisites = message.text
    data = await state.get_data()
    crypto_id = data['crypto_id']

    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE cryptocurrencies SET requisites = ? WHERE id = ?", (new_requisites, crypto_id))
    conn.commit()
    conn.close()

    await message.answer("Реквизиты успешно обновлены.", reply_markup=get_crypto_menu())
    await state.finish()



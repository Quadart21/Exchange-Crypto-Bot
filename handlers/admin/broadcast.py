from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text
from config import dp, bot, ADMIN_ID
from database.db import create_connection, get_operator_id_by_telegram_id
from keyboards.main_menu import get_broadcast_menu, get_back_menu, get_main_menu

class BroadcastStates(StatesGroup):
    select_type = State()
    user_search = State()
    message_content = State()
    confirm_send = State()

@dp.message_handler(Text(equals="🔙 Назад", ignore_case=True), state="*")
async def cancel_state_and_return_to_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.reply("Возврат в главное меню.", reply_markup=get_main_menu(message.from_user.id))


@dp.message_handler(lambda message: message.text == "📤 Рассылка")
async def start_broadcast(message: types.Message):
    if str(message.from_user.id) == ADMIN_ID:  # Проверка на администратора
        # Код для администратора: доступна рассылка всем и одному пользователю
        await message.reply("Выберите тип рассылки:", reply_markup=get_broadcast_menu())
        await BroadcastStates.select_type.set()
    elif get_operator_id_by_telegram_id(message.from_user.id):  # Проверка на оператора
        # Код для оператора: доступна рассылка одному пользователю
        await message.reply("Введите ID или юзернейм пользователя:", reply_markup=get_back_menu())
        await BroadcastStates.user_search.set()
    else:
        # Пользователь не имеет доступа
        await message.reply("У вас нет доступа к этому разделу.")

@dp.message_handler(state=BroadcastStates.select_type)
async def broadcast_type_handler(message: types.Message, state: FSMContext):
    if message.text == "👤 Одному пользователю":
        await message.reply("Введите ID или юзернейм пользователя:", reply_markup=get_back_menu())
        await BroadcastStates.user_search.set()
    elif message.text == "👥 Всем пользователям":
        await message.reply("Введите текст сообщения (поддерживаются HTML-теги):", reply_markup=get_back_menu())
        await BroadcastStates.message_content.set()
    elif message.text == "Назад":
        await cancel_state_and_return_to_menu(message, state)
    else:
        await message.reply("Выберите корректный вариант из меню:", reply_markup=get_broadcast_menu())

@dp.message_handler(state=BroadcastStates.user_search)
async def user_search_handler(message: types.Message, state: FSMContext):
    user_identifier = message.text.strip()
    conn = create_connection()
    cursor = conn.cursor()

    # Поиск пользователя по ID или username
    cursor.execute("SELECT telegram_id FROM users WHERE telegram_id = ? OR username = ?", 
                   (user_identifier, user_identifier))
    result = cursor.fetchone()
    conn.close()

    if result:
        user_id = result[0]
        await state.update_data(user_id=user_id)
        await message.reply("Введите текст сообщения (поддерживаются HTML-теги):", reply_markup=get_back_menu())
        await BroadcastStates.message_content.set()
    else:
        await message.reply("Пользователь не найден. Попробуйте снова:", reply_markup=get_back_menu())

@dp.message_handler(state=BroadcastStates.message_content, content_types=types.ContentTypes.ANY)
async def message_content_handler(message: types.Message, state: FSMContext):
    await state.update_data(content=message)
    confirm_menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    confirm_menu.add(
        types.KeyboardButton("✅ Да"),
        types.KeyboardButton("❌ Нет"),
        types.KeyboardButton("Назад")
    )

    await message.reply("Сообщение готово к отправке. Подтвердить отправку?", reply_markup=confirm_menu)
    await BroadcastStates.confirm_send.set()

@dp.message_handler(state=BroadcastStates.confirm_send)
async def confirm_send_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    content = data.get("content")
    user_id = data.get("user_id", None)

    if message.text == "✅ Да":
        conn = create_connection()
        cursor = conn.cursor()

        if user_id:
            # Отправка одному пользователю
            try:
                await bot.send_message(user_id, content.text, parse_mode="HTML")
                await message.reply("Сообщение успешно отправлено пользователю!", reply_markup=get_back_menu())
            except Exception as e:
                await message.reply(f"Не удалось отправить сообщение: {e}")
        else:
            # Если вдруг это останется, можем добавить проверку
            await message.reply("Ошибка: отсутствует ID пользователя для отправки сообщения.", reply_markup=get_back_menu())

        conn.close()
        await state.finish()

    elif message.text in ["❌ Нет", "Назад"]:
        await message.reply("Рассылка отменена.", reply_markup=get_back_menu())
        await state.finish()
    else:
        await message.reply("Пожалуйста, подтвердите отправку с помощью кнопок.")

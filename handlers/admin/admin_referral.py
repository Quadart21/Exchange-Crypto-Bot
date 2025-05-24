from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from config import dp, bot, ADMIN_ID
from database.db import (
    update_global_referral_percentage,
    set_personal_referral_percentage,
    get_referrals,
    get_withdrawal_requests,
    approve_withdrawal_request,
    reject_withdrawal_request,
    get_withdrawal_amount
)
from keyboards.main_menu import admin_panel_menu
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Состояния для FSM
class ReferralStates(StatesGroup):
    waiting_for_global_percentage = State()
    waiting_for_user_id = State()
    waiting_for_personal_percentage = State()

# Админ-панель - Управление реферальной системой
@dp.message_handler(lambda message: message.text == "Управление рефералами")
async def referral_management(message: types.Message):
    if str(message.from_user.id) not in ADMIN_ID.split(","):
        await message.reply("❌ У вас нет доступа к админ-панели.")
        return

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🔢 Установить общий процент"))
    keyboard.add(KeyboardButton("✏ Установить индивидуальный процент"))
    keyboard.add(KeyboardButton("📋 Список рефералов"))
    keyboard.add(KeyboardButton("🔎 Заявки на вывод"))
    keyboard.add(KeyboardButton("Назад"))

    await message.reply("⚙ *Управление реферальной системой*", reply_markup=keyboard, parse_mode="Markdown")

# Установка общего процента
@dp.message_handler(lambda message: message.text == "🔢 Установить общий процент")
async def ask_global_percentage(message: types.Message):
    await message.reply("Введите новый реферальный процент для всех пользователей:")
    await ReferralStates.waiting_for_global_percentage.set()

@dp.message_handler(state=ReferralStates.waiting_for_global_percentage)
async def set_global_percentage(message: types.Message, state: FSMContext):
    try:
        new_percentage = float(message.text)
        update_global_referral_percentage(new_percentage)
        await message.reply(f"✅ Новый общий реферальный процент: {new_percentage}%")
    except ValueError:
        await message.reply("❌ Ошибка! Введите число.")
    await state.finish()

# Установка индивидуального процента
@dp.message_handler(lambda message: message.text == "✏ Установить индивидуальный процент")
async def ask_user_id(message: types.Message):
    await message.reply("Введите Telegram ID пользователя:")
    await ReferralStates.waiting_for_user_id.set()

@dp.message_handler(state=ReferralStates.waiting_for_user_id)
async def ask_personal_percentage(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)
        await state.update_data(user_id=user_id)
        await message.reply("Введите процент для этого пользователя:")
        await ReferralStates.waiting_for_personal_percentage.set()
    except ValueError:
        await message.reply("❌ Ошибка! Введите числовой ID.")

@dp.message_handler(state=ReferralStates.waiting_for_personal_percentage)
async def set_personal_percentage(message: types.Message, state: FSMContext):
    try:
        percentage = float(message.text)
        data = await state.get_data()
        user_id = data["user_id"]
        set_personal_referral_percentage(user_id, percentage)
        await message.reply(f"✅ Установлен индивидуальный процент {percentage}% для пользователя {user_id}.")
    except ValueError:
        await message.reply("❌ Ошибка! Введите число.")
    await state.finish()

# Список рефералов
@dp.message_handler(lambda message: message.text == "📋 Список рефералов")
async def list_referrals(message: types.Message):
    referrals = get_referrals()
    if not referrals:
        await message.reply("✅ В системе пока нет рефералов.")
        return

    text = "📋 *Список рефералов:*\n\n"
    for ref in referrals:
        text += f"👤 `{ref[0]}` ({ref[1]}) пригласил 👥 `{ref[2]}` ({ref[3]})\n"

    await message.reply(text, parse_mode="Markdown")

# Управление заявками на вывод
@dp.message_handler(lambda message: message.text == "🔎 Заявки на вывод")
async def show_withdraw_requests(message: types.Message):
    requests = get_withdrawal_requests()
    
    if not requests:
        await message.reply("✅ Заявок на вывод нет.")
        return

    for req in requests:
        request_id, user_id, amount, requisites = req  # Добавляем реквизиты

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_withdraw:{request_id}:{user_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_withdraw:{request_id}:{user_id}")
        )

        text = f"🔎 *Заявка на вывод:*\n" \
               f"📌 ID: `{request_id}`\n" \
               f"👤 Пользователь: `{user_id}`\n" \
               f"💰 Сумма: `{amount} USDT`\n" \
               f"📋 Реквизиты: `{requisites}`\n"

        await message.reply(text, parse_mode="Markdown", reply_markup=keyboard)



@dp.callback_query_handler(lambda call: call.data.startswith("approve_withdraw"))
async def approve_withdrawal_callback(call: types.CallbackQuery):
    _, request_id, user_id = call.data.split(":")
    request_id, user_id = int(request_id), int(user_id)

    # Получаем сумму заявки
    amount = get_withdrawal_amount(request_id)
    if amount is None:
        await call.answer("Ошибка: заявка не найдена.", show_alert=True)
        return

    # Обновляем статус заявки
    approve_withdrawal_request(request_id)

    # Оповещаем пользователя
    await bot.send_message(user_id, f"✅ Ваша заявка на вывод #{request_id} на сумму {amount} USDT одобрена. Средства скоро поступят на ваш счет.")

    # Уведомляем администратора
    await call.message.edit_text(f"✅ Заявка #{request_id} на сумму {amount} USDT одобрена.", parse_mode="Markdown")
    await call.answer("Заявка одобрена.")

@dp.callback_query_handler(lambda call: call.data.startswith("reject_withdraw"))
async def reject_withdrawal_callback(call: types.CallbackQuery):
    _, request_id, user_id = call.data.split(":")
    request_id, user_id = int(request_id), int(user_id)

    # Получаем сумму заявки
    amount = get_withdrawal_amount(request_id)
    if amount is None:
        await call.answer("Ошибка: заявка не найдена.", show_alert=True)
        return

    # Обновляем статус заявки
    reject_withdrawal_request(request_id)

    # Оповещаем пользователя
    await bot.send_message(user_id, f"❌ Ваша заявка на вывод #{request_id} на сумму {amount} USDT была отклонена. Свяжитесь с поддержкой.")

    # Уведомляем администратора
    await call.message.edit_text(f"❌ Заявка #{request_id} на сумму {amount} USDT отклонена.", parse_mode="Markdown")
    await call.answer("Заявка отклонена.")

from aiogram import types
from config import dp, bot
from keyboards.main_menu import get_main_menu
from database.db import get_active_orders, get_order_by_id, get_requisites_by_operator, update_order_status
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from database.db import create_connection
from heleket_api import get_invoice_status  # импорт функции API
from aiogram.utils.markdown import escape_md

# Состояния для отклонения заявки
class RejectOrderStates(StatesGroup):
    waiting_for_reason = State()

# Клавиатура действий над заявкой
def create_action_keyboard(order_id):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(f"Одобрить #{order_id}"))
    keyboard.add(KeyboardButton(f"Отклонить #{order_id}"))
    keyboard.add(KeyboardButton(f"🔄 Обновить статус #{order_id}"))
    keyboard.add(KeyboardButton("Главное меню"))
    return keyboard

# Просмотр активных заявок
@dp.message_handler(lambda message: message.text == "Просмотр заявок")
async def show_active_orders(message: types.Message):
    orders = get_active_orders()
    if orders:
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        for order in orders:
            order_id = order[0]
            button_text = f"New #{order_id}: {order[2]}, {order[3]} {order[4]}"
            keyboard.add(KeyboardButton(button_text))
        keyboard.add(KeyboardButton("Главное меню"))
        await message.reply("🔔 *Список активных заявок:*", parse_mode="Markdown", reply_markup=keyboard)
    else:
        await message.reply("✅ Активных заявок нет.", reply_markup=get_main_menu(message.from_user.id))

# Просмотр заявки
@dp.message_handler(lambda message: message.text.startswith("New #"))
async def view_order(message: types.Message):
    try:
        order_id = int(message.text.split("#")[1].strip().split(":")[0])
        order_data = get_order_by_id(order_id, is_admin=True)
        if order_data:
            conn = create_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT type, label, details FROM requisites")
            rows = cursor.fetchall()
            conn.close()

            def line(label, details):
                return f"- {label}: {details}"

            fiat_requisites = "\n".join([
                line(label, details)
                for (typ, label, details) in rows if typ == "fiat"
            ]) or "Нет данных"

            crypto_requisites = "\n".join([
                line(label, details)
                for (typ, label, details) in rows if typ == "crypto"
            ]) or "Нет данных"

            screenshot_id = None
            clean_details_lines = []
            for line_text in order_data['details'].split("\n") if order_data['details'] else []:
                if line_text.startswith("Скриншот:"):
                    screenshot_id = line_text.split("Скриншот:")[-1].strip()
                else:
                    clean_details_lines.append(line_text)
            clean_details = "\n".join(clean_details_lines)

            currency = order_data['currency']
            status = order_data['status']
            created_at = order_data.get("created_at", "Не указана")
            order_type = order_data['type']
            rate = order_data.get('rate', '—')

            if order_type == "sell":
                response = (
                    f"📄 ЗАЯВКА НА ПРОДАЖУ #{order_data['id']}:\n"
                    f"👤 Пользователь: {order_data['user_id']}\n"
                    f"💱 Токен: {currency}\n"
                    f"💰 Кол-во на продажу: {order_data['amount']}\n"
                    f"📈 Курс: {rate} BYN\n"
                    f"💵 Сумма к выплате: {order_data['total']} BYN\n\n"
                    f"📋 Реквизиты пользователя:\n{clean_details}\n\n"
                    f"📈 Статус: {status}\n"
                    f"📅 Дата создания: {created_at}\n\n"
                    f"💳 Наши реквизиты:\n"
                    f"Фиат:\n{fiat_requisites}\n"
                    f"Крипто:\n{crypto_requisites}"
                )
            else:
                response = (
                    f"📄 ЗАЯВКА НА ПОКУПКУ #{order_data['id']}:\n"
                    f"👤 Пользователь: {order_data['user_id']}\n"
                    f"💵 Сумма оплаты: {order_data['total']} BYN\n"
                    f"💱 Токен: {currency}\n"
                    f"🔄 Кол-во к выдаче: {order_data['amount']}\n"
                    f"📈 Курс: {rate} BYN\n\n"
                    f"📋 Реквизиты пользователя:\n{clean_details}\n\n"
                    f"📈 Статус: {status}\n"
                    f"📅 Дата создания: {created_at}\n\n"
                    f"💳 Наши реквизиты:\n"
                    f"Фиат:\n{fiat_requisites}\n"
                    f"Крипто:\n{crypto_requisites}"
                )

            markup = create_action_keyboard(order_data['id'])

            if screenshot_id:
                try:
                    await bot.send_photo(
                        chat_id=message.chat.id,
                        photo=screenshot_id,
                        caption=response,
                        reply_markup=markup
                    )
                except Exception as e:
                    await message.reply(
                        f"⚠️ Не удалось загрузить скриншот: {str(e)}"
                    )
            else:
                await message.reply(response, reply_markup=markup)
        else:
            await message.reply("❌ Заявка не найдена.")
    except ValueError:
        await message.reply("❌ Некорректный формат. Укажите номер заявки, например: 'Заявка #123'")

# Хендлер обновления статуса заявки через Heleket
@dp.message_handler(lambda message: message.text.startswith("🔄 Обновить статус #"))
async def refresh_status(message: types.Message):
    from heleket_api import get_invoice_status
    try:
        order_id = int(message.text.split("#")[1].strip())
        order = get_order_by_id(order_id, is_admin=True)
        if not order:
            return await message.reply("❌ Заявка не найдена.")

        uuid = order.get("uuid")
        if not uuid:
            return await message.reply("⚠️ У заявки нет UUID в базе.")

        result = get_invoice_status(uuid)
        status = result.get("result", {}).get("status")
        if not status:
            return await message.reply("⚠️ Не удалось получить статус от API.")

        if status in ["paid", "paid_over"]:
            await message.reply(f"✅ Оплата найдена для заявки #{order_id}.\nСтатус: `{status}`", parse_mode="Markdown")
        else:
            await message.reply(f"📌 Текущий статус заявки #{order_id}: `{status}`", parse_mode="Markdown")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

# Одобрение заявки
@dp.message_handler(lambda message: message.text.startswith("Одобрить #"))
async def approve_order(message: types.Message):
    try:
        order_id = int(message.text.split("#")[1].strip())
        order_data = get_order_by_id(order_id, is_admin=True)
        if order_data:
            update_order_status(order_id, "confirmed")
            await bot.send_message(
                chat_id=order_data['user_id'],
                text=f"✅ Ваша заявка #{order_id} была одобрена. Спасибо за использование нашего сервиса!"
            )
            await message.reply(f"✅ Заявка #{order_id} одобрена.", reply_markup=get_main_menu(message.from_user.id))
        else:
            await message.reply("❌ Заявка не найдена.")
    except ValueError:
        await message.reply("❌ Некорректный формат. Попробуйте снова.")

# Отклонение заявки
@dp.message_handler(lambda message: message.text.startswith("Отклонить #"))
async def reject_order_start(message: types.Message, state: FSMContext):
    try:
        order_id = int(message.text.split("#")[1].strip())
        await state.update_data(order_id=order_id)
        await RejectOrderStates.waiting_for_reason.set()
        await message.reply("❗ Укажите причину отказа:", reply_markup=types.ReplyKeyboardRemove())
    except ValueError:
        await message.reply("❌ Некорректный формат. Попробуйте снова.")

@dp.message_handler(state=RejectOrderStates.waiting_for_reason)
async def reject_order_reason(message: types.Message, state: FSMContext):
    reason = message.text
    state_data = await state.get_data()
    order_id = state_data['order_id']
    order_data = get_order_by_id(order_id, is_admin=True)
    if order_data:
        update_order_status(order_id, "rejected")
        await bot.send_message(
            chat_id=order_data['user_id'],
            text=f"❌ Ваша заявка #{order_id} была отклонена.\nПричина отказа: {reason}"
        )
        await message.reply(f"❌ Заявка #{order_id} отклонена по причине: {reason}.", reply_markup=get_main_menu(message.from_user.id))
    else:
        await message.reply("❌ Заявка не найдена.", reply_markup=get_main_menu(message.from_user.id))
    await state.finish()

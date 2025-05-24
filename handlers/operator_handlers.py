from aiogram import types
import aiohttp
import logging
from config import dp, bot, CHANNEL_ID, NOWNODES_API_KEY
from keyboards.main_menu import operator_menu, get_main_menu
from database.db import (
    get_active_orders, 
    get_username_by_user_id, 
    get_order_by_id, 
    update_order_status, 
    get_operator_id_by_telegram_id, 
    get_requisites_by_operator,
    get_operators
)
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# Список допустимых статусов для обработки заявки
ALLOWED_STATUSES = ['screenshot_uploaded', 'hash_provided']

# Состояния для отклонения заявки
class RejectOrderStates(StatesGroup):
    waiting_for_reason = State()

# Создание клавиатуры с кнопками для действий над заявкой
def create_action_keyboard(order_id):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(f"Одобрить заявку #{order_id}"))
    keyboard.add(KeyboardButton(f"Отклонить заявку #{order_id}"))
    keyboard.add(KeyboardButton("Интерфейс оператора"))
    return keyboard

class ReviewStates(StatesGroup):
    waiting_for_review = State()

# Клавиатура с активными заявками
def create_active_orders_keyboard(orders):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for order in orders:
        order_id = order[0]
        button_text = f"Заявка #{order_id}: {order[2]}, {order[3]} {order[4]}"
        keyboard.add(KeyboardButton(button_text))
    keyboard.add(KeyboardButton("Интерфейс оператора"))
    return keyboard

# Интерфейс оператора
@dp.message_handler(lambda message: message.text == "Интерфейс оператора")
async def operator_interface(message: types.Message):
    await message.reply(
        "🔧 Добро пожаловать в интерфейс оператора. Выберите действие:", 
        reply_markup=operator_menu()
    )

# Отображение активных заявок
@dp.message_handler(lambda message: message.text == "Активные заявки")
async def show_active_orders(message: types.Message):
    telegram_id = message.from_user.id
    operator_id = get_operator_id_by_telegram_id(telegram_id)

    if operator_id is None:
        await message.reply("❌ Вы не зарегистрированы как оператор.", reply_markup=get_main_menu(message.from_user.id))
        return

    # Проверяем статус оператора
    operators = get_operators()
    operator_data = next((op for op in operators if op[0] == operator_id), None)

    if not operator_data:
        await message.reply("❌ Оператор не найден.", reply_markup=get_main_menu(message.from_user.id))
        return

    if operator_data[3] == "inactive":  # Проверка статуса оператора
        await message.reply("✅ У вас нет доступа к активным заявкам, так как ваш статус: `inactive`.", parse_mode="Markdown", reply_markup=operator_menu())
        return

    # Получение активных заявок
    orders = get_active_orders(operator_id)
    if orders:
        keyboard = create_active_orders_keyboard(orders)
        await message.reply("🔔 *Список активных заявок:*", parse_mode="Markdown", reply_markup=keyboard)
    else:
        await message.reply("✅ Активных заявок нет.", reply_markup=operator_menu())

# Обработчик сообщения, начинающегося с "Заявка #"


async def get_trx_transaction_info(tx_hash: str):
    """
    Получить информацию о транзакции через Tronscan API.
    Подходит для TRC-20, TRX, USDT в сети TRON.
    """
    url = f"https://apilist.tronscan.org/api/transaction-info?hash={tx_hash}"

    logging.info(f"📡 Отправка запроса в Tronscan по хэшу: {tx_hash}")
    logging.info(f"🌐 URL запроса: {url}")

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            logging.info(f"📥 Статус ответа: {resp.status}")
            try:
                data = await resp.json()
                logging.info(f"📦 Ответ от Tronscan:\n{data}")
                return data if resp.status == 200 else None
            except Exception as e:
                logging.error(f"❌ Ошибка парсинга JSON: {e}")
                return None           

@dp.message_handler(lambda message: message.text.startswith("Заявка #"))
async def view_order(message: types.Message):
    try:
        order_id = int(message.text.split("#")[1].strip().split(":")[0])
        telegram_id = message.from_user.id
        operator_id = get_operator_id_by_telegram_id(telegram_id)

        if operator_id is None:
            await message.reply("❌ Вы не зарегистрированы как оператор.", reply_markup=get_main_menu(message.from_user.id))
            return

        order_data = get_order_by_id(order_id)
        if not order_data:
            await message.reply(f"❌ Заявка #{order_id} не найдена.")
            return

        if order_data.get('operator_id') != operator_id:
            await message.reply(f"❌ Заявка #{order_id} не принадлежит вам.")
            return

        if order_data['status'] not in ['screenshot_uploaded', 'hash_provided']:
            await message.reply(
                f"⚠️ Нельзя одобрить или отклонить заявку до предоставления скриншота или хэша.\n\n"
                f"Текущий статус заявки: {order_data['status']}.",
                reply_markup=create_action_keyboard(order_id)
            )
            return

        user_id = order_data['user_id']
        username = get_username_by_user_id(user_id) or "Неизвестный пользователь"
        requisites = get_requisites_by_operator(operator_id)

        fiat_requisites = "\n".join([f"- {item[0]}: {item[1]}" for item in requisites['fiat']])
        crypto_requisites = "\n".join([f"- {item[0]}: {item[1]}" for item in requisites['crypto']])

        # Получение ID скриншота
        screenshot_id = None
        if order_data['details']:
            for line in order_data['details'].split("\n"):
                if line.startswith("Screenshot ID:"):
                    screenshot_id = line.split("Screenshot ID:")[-1].strip()

        # Сбор информации о заявке
        response = (
            f"📄 Информация о заявке #{order_data['id']}:\n"
            f"👤 Пользователь: {username} (ID: {user_id})\n"
            f"🔄 Тип: {order_data['type']}\n"
            f"💰 Сумма: {order_data['amount']}\n"
            f"💵 Итоговая сумма: {order_data['total']}\n"
            f"📈 Статус: {order_data['status']}\n"
            f"💱 Валюта: {order_data['currency']}\n"
            f"📋 Реквизиты пользователя: {order_data['details']}\n"
            f"📅 Дата создания: {order_data.get('created_at', 'Не указана')}\n\n"
            f"💳 *Наши реквизиты:*\n"
            f"📑 **Фиат:**\n{fiat_requisites}\n"
        )
        await message.reply(response, reply_markup=create_action_keyboard(order_id))

        # Скриншот
        if screenshot_id:
            try:
                await bot.send_photo(chat_id=message.chat.id, photo=screenshot_id)
            except Exception as e:
                await message.reply(f"⚠️ Не удалось загрузить скриншот: {e}")
        else:
            await message.reply("📷 Скриншот отсутствует.")

        # 🔍 Проверка TRON/USDT транзакции через Tronscan
        if any(kw in order_data["currency"].lower() for kw in ["trx", "trc", "usdt"]):
            tx_hash = None
            for line in (order_data["details"] or "").splitlines():
                if "Transaction Hash:" in line:
                    tx_hash = line.split("Transaction Hash:")[-1].strip()

            if tx_hash:
                await message.reply("🔍 Проверка TRON-транзакции через Tronscan...")

                trx_data = await get_trx_transaction_info(tx_hash)

                if trx_data:
                    to_address = trx_data.get("toAddress", "")
                    confirmations = trx_data.get("confirmations") or trx_data.get("confirmed")
                    success = trx_data.get("contractRet") == "SUCCESS"

                    # Получение ожидаемого адреса из реквизитов оператора
                    operator_crypto_address = None
                    currency_label = order_data['currency'].split()[0].upper()
                    for name, address in requisites['crypto']:
                        if name.upper() == currency_label:
                            operator_crypto_address = address
                            break

                    if to_address.lower() == (operator_crypto_address or "").lower():
                        await message.reply(
                            f"✅ Транзакция найдена.\n"
                            f"📬 Получатель: `{to_address}`\n"
                            f"📦 Статус: {'успешно' if success else 'ошибка'}\n"
                            f"🔁 Подтверждений: {confirmations}"
                        )
                    else:
                        await message.reply(
                            f"⚠️ Транзакция найдена, но адрес получателя не совпадает с реквизитами оператора.\n"
                            f"🧾 Из транзакции: `{to_address}`\n"
                            f"🧾 Ожидался: `{operator_crypto_address}`"
                        )
                else:
                    await message.reply("❌ Транзакция не найдена через Tronscan.")
    except ValueError:
        await message.reply("❌ Некорректный формат. Укажите номер заявки, например: 'Заявка #123'")


# Одобрение заявки
@dp.message_handler(lambda message: message.text.startswith("Одобрить заявку #"))
async def approve_order(message: types.Message):
    try:
        order_id = int(message.text.split("#")[1].strip())
        telegram_id = message.from_user.id
        operator_id = get_operator_id_by_telegram_id(telegram_id)

        if operator_id is None:
            await message.reply("❌ Вы не зарегистрированы как оператор.", reply_markup=get_main_menu(message.from_user.id))
            return

        order_data = get_order_by_id(order_id)
        if not order_data:
            await message.reply("❌ Заявка не найдена.", reply_markup=get_main_menu(message.from_user.id))
            return

        # Проверка статуса заявки
        if order_data['status'] not in ALLOWED_STATUSES:
            await message.reply(
                f"⚠️ Нельзя одобрить заявку до предоставления скриншота или хэша.\n\n"
                f"Текущий статус заявки: {order_data['status']}.",
                reply_markup=get_main_menu(message.from_user.id)
            )
            return

        # Обновление статуса
        update_order_status(order_id, "confirmed", operator_id)

        # Уведомление пользователя
        user_id = order_data['user_id']
        await bot.send_message(
            chat_id=user_id,
            text=f"✅ Ваша заявка #{order_id} была одобрена оператором. Спасибо за использование нашего сервиса!"
        )

        # Предложение оставить отзыв
        review_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        review_keyboard.add(KeyboardButton("Да"), KeyboardButton("Нет"))
        await bot.send_message(
            chat_id=user_id,
            text="Хотите оставить отзыв о работе сервиса?",
            reply_markup=review_keyboard
        )

        # Ответ оператору
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton("Интерфейс оператора"))
        await message.reply(f"✅ Заявка #{order_id} одобрена.", reply_markup=keyboard)
    except ValueError:
        await message.reply("❌ Некорректный формат. Попробуйте снова.", reply_markup=get_main_menu(message.from_user.id))


# Обработка ответа пользователя на предложение оставить отзыв
@dp.message_handler(lambda message: message.text == "Да")
async def ask_for_review(message: types.Message, state: FSMContext):
    await ReviewStates.waiting_for_review.set()
    await message.reply("Пожалуйста, напишите ваш отзыв о работе сервиса.", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda message: message.text == "Нет")
async def decline_review(message: types.Message):
    await message.reply("Спасибо! Мы рады, что вы воспользовались нашим сервисом.", reply_markup=get_main_menu(message.from_user.id))

# Получение отзыва и публикация в канал
@dp.message_handler(state=ReviewStates.waiting_for_review)
async def publish_review(message: types.Message, state: FSMContext):
    review_text = message.text

    try:
        # Публикация отзыва в канале
        await bot.send_message(chat_id=CHANNEL_ID, text=f"📝 Новый отзыв:\n\n{review_text}")
        await message.reply("Спасибо за ваш отзыв! Он был опубликован.", reply_markup=get_main_menu(message.from_user.id))
    except Exception as e:
        await message.reply(f"⚠️ Не удалось опубликовать отзыв: {e}", reply_markup=get_main_menu(message.from_user.id))

    await state.finish()

# Отклонение заявки
@dp.message_handler(lambda message: message.text.startswith("Отклонить заявку #"))
async def reject_order_start(message: types.Message, state: FSMContext):
    try:
        order_id = int(message.text.split("#")[1].strip())
        telegram_id = message.from_user.id
        operator_id = get_operator_id_by_telegram_id(telegram_id)

        if operator_id is None:
            await message.reply("❌ Вы не зарегистрированы как оператор.", reply_markup=get_main_menu(message.from_user.id))
            return

        order_data = get_order_by_id(order_id)
        if not order_data:
            await message.reply("❌ Заявка не найдена.", reply_markup=get_main_menu(message.from_user.id))
            return

        # Проверка статуса заявки
        if order_data['status'] not in ALLOWED_STATUSES:
            await message.reply(
                f"⚠️ Нельзя отклонить заявку до предоставления скриншота или хэша.\n\n"
                f"Текущий статус заявки: {order_data['status']}.",
                reply_markup=get_main_menu(message.from_user.id)
            )
            return

        # Сохранение ID заявки и ожидание причины
        await state.update_data(order_id=order_id)
        await RejectOrderStates.waiting_for_reason.set()
        await message.reply("❗ Укажите причину отказа:", reply_markup=types.ReplyKeyboardRemove())
    except ValueError:
        await message.reply("❌ Некорректный формат. Попробуйте снова.", reply_markup=get_main_menu(message.from_user.id))

@dp.message_handler(state=RejectOrderStates.waiting_for_reason)
async def reject_order_reason(message: types.Message, state: FSMContext):
    reason = message.text
    state_data = await state.get_data()
    order_id = state_data['order_id']

    telegram_id = message.from_user.id
    operator_id = get_operator_id_by_telegram_id(telegram_id)

    if operator_id is None:
        await message.reply("❌ Вы не зарегистрированы как оператор.", reply_markup=get_main_menu(message.from_user.id))
        await state.finish()
        return

    # Обновление статуса
    update_order_status(order_id, "rejected", operator_id)

    # Уведомление пользователя
    order_data = get_order_by_id(order_id)
    user_id = order_data['user_id']
    await bot.send_message(
        chat_id=user_id,
        text=f"❌ Ваша заявка #{order_id} была отклонена оператором.\nПричина отказа: {reason}"
    )

    # Ответ оператору
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Интерфейс оператора"))
    await message.reply(f"❌ Заявка #{order_id} отклонена по причине: {reason}.", reply_markup=keyboard)
    await state.finish()

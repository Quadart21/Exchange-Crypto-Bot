import uuid
import datetime
import time
import logging
from threading import Thread

from fastapi import FastAPI, Request
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

from config import dp, MARKUP_SELL_USD, MARKUP_SELL_OTHER
from database.db import create_connection, update_order_status, get_user_role
from heleket_api import create_invoice, get_available_tokens_and_networks, verify_webhook, get_exchange_rate_heleket_reversed
from binance_parser import BinanceP2PParser
from dzengi_parser import DzengiRatesClient
from keyboards.main_menu import get_main_menu, get_cancel_menu
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",)

class SellCryptoFSM(StatesGroup):
    waiting_for_token = State()
    waiting_for_network = State()
    waiting_for_amount = State()
    waiting_for_requisites = State()
    waiting_for_final_confirm = State()

user_sell_data = {}
app = FastAPI()
dzengi_client = DzengiRatesClient(api_key='X06LLPYuvunhfvUe', secret_key='BSSrMlsRKs/IiPh6y$9V2Zrn_tDjy_#9')

@dp.message_handler(lambda m: m.text == "❌ Отмена", state="*")
async def cancel_sell_process(msg: types.Message, state: FSMContext):
    await state.finish()
    role = get_user_role(msg.from_user.id)
    await msg.answer("❌ Операция отменена. Главное меню:", reply_markup=get_main_menu(msg.from_user.id, role))
    user_sell_data.pop(msg.from_user.id, None)

async def calculate_full_rate(token: str, markup: float):
    try:
        if token in ['USDT', 'USDC']:
            token_to_usdt = 1.0
        else:
            token_to_usdt = get_exchange_rate_heleket_reversed(token)
            if not token_to_usdt or token_to_usdt <= 0:
                return None

        usd_to_byn = dzengi_client.get_usd_byn_bid()
        if usd_to_byn <= 0:
            return None

        final_rate = token_to_usdt * usd_to_byn
        if markup != 0:
            final_rate *= (1 + markup / 100)

        return final_rate
    except Exception:
        return None

@dp.message_handler(lambda message: message.text == "💰 Продать")
async def sell_crypto_start(message: types.Message):
    user_id = message.from_user.id
    user_sell_data[user_id] = {}
    tokens_networks = get_available_tokens_and_networks()
    user_sell_data[user_id]['tokens_networks'] = tokens_networks

    keyboard = InlineKeyboardMarkup(row_width=3)
    for token in tokens_networks.keys():
        keyboard.insert(InlineKeyboardButton(token, callback_data=f"sell_token:{token}"))

    await message.answer("Выберите криптовалюту для продажи:", reply_markup=keyboard)
    await message.answer("❌ Вы можете отменить в любой момент.", reply_markup=get_cancel_menu())
    await SellCryptoFSM.waiting_for_token.set()

@dp.callback_query_handler(lambda call: call.data.startswith("sell_token"), state=SellCryptoFSM.waiting_for_token)
async def sell_choose_token(call: types.CallbackQuery, state: FSMContext):
    token = call.data.split(":")[1]
    user_id = call.from_user.id
    if user_id not in user_sell_data:
        await call.message.answer("Сессия устарела. Попробуйте заново.")
        return

    user_sell_data[user_id]['token'] = token
    networks = user_sell_data[user_id]['tokens_networks'].get(token, [])

    if len(networks) > 1:
        keyboard = InlineKeyboardMarkup(row_width=2)
        for net in networks:
            keyboard.insert(InlineKeyboardButton(net, callback_data=f"sell_net:{net}"))
        await call.message.edit_text("Выберите сеть:", reply_markup=keyboard)
        await SellCryptoFSM.waiting_for_network.set()
    else:
        user_sell_data[user_id]['network'] = networks[0]
        await ask_amount(call.message)

@dp.callback_query_handler(lambda call: call.data.startswith("sell_net"), state=SellCryptoFSM.waiting_for_network)
async def sell_choose_network(call: types.CallbackQuery, state: FSMContext):
    network = call.data.split(":")[1]
    user_id = call.from_user.id
    if user_id not in user_sell_data:
        await call.message.answer("Сессия устарела. Попробуйте заново.")
        return
    user_sell_data[user_id]['network'] = network
    await ask_amount(call.message)

async def ask_amount(message):
    await message.answer("Введите количество токенов, которое хотите продать:", reply_markup=get_cancel_menu())
    await SellCryptoFSM.waiting_for_amount.set()

@dp.message_handler(state=SellCryptoFSM.waiting_for_amount)
async def sell_enter_amount(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in user_sell_data:
        await message.answer("Сессия устарела. Попробуйте заново.", reply_markup=get_cancel_menu())
        return

    try:
        amount = float(message.text.replace(",", "."))
        user_sell_data[user_id]['amount'] = amount

        token = user_sell_data[user_id]['token']
        is_usd = token in ["USDT", "USDC"]
        markup = MARKUP_SELL_USD if is_usd else MARKUP_SELL_OTHER

        base_rate = await calculate_full_rate(token, 0)
        rate = await calculate_full_rate(token, markup)

        if not base_rate or not rate or rate <= 0:
            await message.answer("❌ Невозможно продать выбранную монету. Попробуйте другую.", reply_markup=get_cancel_menu())
            return

        await message.answer(
            f"📈 Курс <code>{rate:.6f} BYN</code>",
            parse_mode="HTML", reply_markup=get_cancel_menu()
        )

        display_rate = round(rate, 8 if rate < 0.01 else 2)
        total = round(amount * display_rate, 2)

        user_sell_data[user_id]['rate'] = display_rate
        user_sell_data[user_id]['total_byn'] = total

        text = (
            f"<b>📋 Продажа:</b> <code>{amount} {token}</code>\n"
            f"💱 <b>Курс:</b> <code>{display_rate} BYN</code>\n"
            f"💰 <b>Итого к получению:</b> <code>{total:.2f} BYN</code>\n\n"
            f"❓ Подтверждаете продажу?"
        )

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("✅ Да", callback_data="confirm_amount"))
        keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))

        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    except ValueError:
        await message.answer("⚠️ Введите корректное число!", reply_markup=get_cancel_menu())

@dp.callback_query_handler(lambda call: call.data == "confirm_amount", state=SellCryptoFSM.waiting_for_amount)
async def sell_confirm_amount(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📨 Введите реквизиты для получения BYN:", reply_markup=get_cancel_menu())
    await SellCryptoFSM.waiting_for_requisites.set()

@dp.message_handler(state=SellCryptoFSM.waiting_for_requisites)
async def sell_enter_requisites(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in user_sell_data:
        await message.answer("Сессия устарела. Попробуйте заново.", reply_markup=get_cancel_menu())
        return

    user_sell_data[user_id]['requisites'] = message.text
    data = user_sell_data[user_id]

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("✅ Подтвердить продажу", callback_data="final_confirm"))
    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))

    await message.answer(
        f"<b>🔎 Проверьте данные перед созданием заявки:</b>\n"
        f"🔹 Токен: <code>{data['token']}</code>\n"
        f"🔹 Сеть: <code>{data['network']}</code>\n"
        f"🔹 Кол-во: <code>{data['amount']}</code>\n"
        f"🔹 Курс: <code>{data['rate']} BYN</code>\n"
        f"🔹 Итого: <code>{data['total_byn']} BYN</code>\n"
        f"🔹 Реквизиты: <code>{data['requisites']}</code>\n\n"
        f"✅ Подтвердите заявку!",
        parse_mode="HTML", reply_markup=keyboard
    )
    await message.answer("❌ Вы можете отменить до подтверждения заявки.", reply_markup=get_cancel_menu())
    await SellCryptoFSM.waiting_for_final_confirm.set()

@dp.callback_query_handler(lambda call: call.data == "final_confirm", state=SellCryptoFSM.waiting_for_final_confirm)
async def sell_create_invoice(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    if user_id not in user_sell_data:
        await call.message.answer("Сессия устарела. Попробуйте заново.")
        return

    data = user_sell_data[user_id]
    order_id = str(uuid.uuid4())

    invoice = create_invoice(
        amount=data['amount'],
        currency=data['token'],
        order_id=order_id,
        network=data['network'],
        url_callback="http://45.8.147.242:8000/webhook"
    )

    if invoice.get("state") != 0:
        await call.message.answer("Ошибка создания инвойса.")
        return

    address = invoice['result']['address']
    invoice_uuid = invoice['result']['uuid']

    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders (user_id, type, amount, rate, total, status, details, currency, requisites, created_at, uuid)
        VALUES (?, 'sell', ?, ?, ?, 'new', ?, ?, ?, ?, ?)
    """, (
        user_id,
        data['amount'],
        data['rate'],
        data['total_byn'],
        data['requisites'],          # details → реквизиты
        data['token'],
        data['requisites'],          # requisites → реквизиты
        datetime.datetime.now(),
        invoice_uuid
    ))
    conn.commit()
    conn.close()

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📤 Я отправил деньги", callback_data="i_paid"))

    await call.message.answer(
        f"<b>⚠️ ВАЖНО:</b> Отправьте ровно <code>{data['amount']} {data['token']}</code> "
        f"на адрес в сети <b>{data['network'].upper()}</b> ниже:\n\n"
        f"<code>{address}</code>\n\n"
        f"После отправки нажмите кнопку ниже.",
        parse_mode="HTML", reply_markup=keyboard
    )

    await call.message.answer("⌨️ Меню скрыто до завершения операции.", reply_markup=ReplyKeyboardRemove())
    await state.finish()

@dp.callback_query_handler(lambda call: call.data == "i_paid", state="*")
async def handle_user_paid(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM orders WHERE user_id=? AND type='sell' ORDER BY created_at DESC LIMIT 1", (user_id,))
    row = cursor.fetchone()

    if not row:
        await call.message.answer("❌ Заявка не найдена.")
        return

    update_order_status(row[0], "screenshot_uploaded", None)
    await call.message.answer("✅ Заявка отправлена оператору. Ожидайте подтверждения.")

    role = get_user_role(user_id)
    await call.message.answer("🏠 Вы возвращены в главное меню:", reply_markup=get_main_menu(user_id, role))

@dp.callback_query_handler(lambda call: call.data == "cancel", state="*")
async def sell_cancel(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("❌ Продажа отменена.")
    await state.finish()
    user_sell_data.pop(call.from_user.id, None)

@app.post("/webhook")
async def webhook_handler(request: Request):
    data = await request.json()
    if not verify_webhook(data):
        return {"status": "invalid signature"}
    if data.get("status") in ["paid", "paid_over"]:
        update_order_status(data.get("order_id"), "paid", details=str(data))
    return {"status": "ok"}

def auto_cancel_unpaid_orders():
    while True:
        try:
            conn = create_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE orders
                SET status = 'cancel'
                WHERE status = 'new' AND created_at <= datetime('now', '-30 minutes')
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logging.exception(f"[AUTO_CANCEL] Ошибка автоотмены: {e}")
        time.sleep(300)

Thread(target=auto_cancel_unpaid_orders, daemon=True).start()

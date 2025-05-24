from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

from config import dp, MARKUP_BUY_USD, MARKUP_BUY_OTHER
from heleket_api import get_available_tokens_and_networks, get_exchange_rate_heleket_ask
from dzengi_parser import DzengiRatesClient
from database.db import get_user_role, create_connection
from keyboards.main_menu import get_main_menu, get_cancel_menu

# FSM-состояния
class BuyCryptoFSM(StatesGroup):
    waiting_for_token = State()
    waiting_for_network = State()
    waiting_for_amount_type = State()
    waiting_for_amount_value = State()
    waiting_for_wallet = State()
    confirm_order = State()
    waiting_for_screenshot = State()

dzengi = DzengiRatesClient()

@dp.message_handler(lambda m: m.text == "❌ Отмена", state="*")
async def cancel_buy_process(msg: types.Message, state: FSMContext):
    await state.finish()
    role = get_user_role(msg.from_user.id)
    await msg.answer("❌ Операция отменена. Главное меню:", reply_markup=get_main_menu(msg.from_user.id, role))

@dp.message_handler(text="💲 Купить")
async def buy_start(msg: types.Message):
    tokens_data = get_available_tokens_and_networks()
    await dp.current_state(user=msg.from_user.id).update_data(tokens_data=tokens_data)
    keyboard = InlineKeyboardMarkup(row_width=4)
    for token in tokens_data.keys():
        keyboard.insert(InlineKeyboardButton(token, callback_data=f"buy_token_{token}"))
    await msg.answer("🔘 Выберите криптовалюту для покупки:", reply_markup=keyboard)
    await msg.answer("❌ Вы можете отменить в любой момент.", reply_markup=get_cancel_menu())
    await BuyCryptoFSM.waiting_for_token.set()

@dp.callback_query_handler(lambda c: c.data.startswith("buy_token_"), state=BuyCryptoFSM.waiting_for_token)
async def select_token(call: types.CallbackQuery, state: FSMContext):
    token = call.data.split("_")[-1]
    data = await state.get_data()
    networks = data["tokens_data"].get(token, [])
    await state.update_data(token=token)
    keyboard = InlineKeyboardMarkup(row_width=3)
    for net in networks:
        keyboard.insert(InlineKeyboardButton(net, callback_data=f"buy_net_{net}"))
    await call.message.edit_text(f"✅ Вы выбрали: <b>{token}</b>\n📡 Выберите сеть:", parse_mode="HTML", reply_markup=keyboard)
    await BuyCryptoFSM.waiting_for_network.set()

@dp.callback_query_handler(lambda c: c.data.startswith("buy_net_"), state=BuyCryptoFSM.waiting_for_network)
async def select_network(call: types.CallbackQuery, state: FSMContext):
    network = call.data.split("_")[-1]
    await state.update_data(network=network)
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("💰 Ввести в BYN", callback_data="amount_type_BYN"),
        InlineKeyboardButton("🪙 Ввести в токене", callback_data="amount_type_TOKEN"),
    )
    await call.message.edit_text("Как хотите указать сумму?", reply_markup=keyboard)
    await BuyCryptoFSM.waiting_for_amount_type.set()

@dp.callback_query_handler(lambda c: c.data.startswith("amount_type_"), state=BuyCryptoFSM.waiting_for_amount_type)
async def choose_amount_type(call: types.CallbackQuery, state: FSMContext):
    value = call.data.split("_")[-1]
    await state.update_data(amount_type=value)
    await call.message.answer(f"Введите сумму в {value}:", reply_markup=get_cancel_menu())
    await BuyCryptoFSM.waiting_for_amount_value.set()

@dp.message_handler(lambda m: m.text.replace('.', '', 1).isdigit(), state=BuyCryptoFSM.waiting_for_amount_value)
async def enter_amount(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    amount = float(msg.text)
    token = data['token']
    network = data['network']
    amount_type = data['amount_type']

    rate_token_to_usdt = get_exchange_rate_heleket_ask(token)
    rate_usd_to_byn = dzengi.get_usd_byn_bid()
    if rate_token_to_usdt == 0 or rate_usd_to_byn == 0:
        return await msg.answer("Ошибка получения курса. Попробуйте позже.", reply_markup=get_cancel_menu())

    is_usd = token in ["USDT", "USDC"]
    markup = MARKUP_BUY_USD if is_usd else MARKUP_BUY_OTHER
    rate_with_markup = rate_token_to_usdt * (1 + markup / 100)

    await msg.answer(
        
        f"📈 Курс: <code>{rate_with_markup:.6f} USDT</code>",
        parse_mode="HTML",
        reply_markup=get_cancel_menu()
    )

    if amount_type == "BYN":
        usdt = amount / rate_usd_to_byn
        tokens = usdt / rate_with_markup
    else:
        tokens = amount
        usdt = tokens * rate_with_markup
        amount = usdt * rate_usd_to_byn

    await state.update_data(byn=round(amount, 2), tokens=round(tokens, 8))

    await msg.answer(
        f"Вы получите: {tokens:.8f} {token}\nК оплате: {amount:.2f} BYN\n\nВведите адрес кошелька:",
        reply_markup=get_cancel_menu()
    )
    await BuyCryptoFSM.waiting_for_wallet.set()

@dp.message_handler(state=BuyCryptoFSM.waiting_for_wallet)
async def input_wallet(msg: types.Message, state: FSMContext):
    wallet = msg.text
    await state.update_data(wallet=wallet)
    data = await state.get_data()
    text = (
        f"Подтвердите заявку:\n\n"
        f"Токен: {data['token']}\n"
        f"Сеть: {data['network']}\n"
        f"Сумма к оплате: {data['byn']} BYN\n"
        f"Вы получите: {data['tokens']} {data['token']}\n"
        f"Кошелёк: `{wallet}`\n\n"
        f"*Убедитесь в правильности адреса и сети. Возврат невозможен!*"
    )
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_order"))
    await msg.answer(text, parse_mode="Markdown", reply_markup=keyboard)
    await msg.answer("❌ Вы можете отменить в любой момент.", reply_markup=get_cancel_menu())
    await BuyCryptoFSM.confirm_order.set()

@dp.callback_query_handler(text="confirm_order", state=BuyCryptoFSM.confirm_order)
async def confirm_order(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = call.from_user.id

    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders (user_id, type, amount, rate, total, currency, status, details)
        VALUES (?, ?, ?, ?, ?, ?, 'new', ?)
    """, (
        user_id, "buy", data['tokens'], data['byn'] / data['tokens'], data['byn'],
        data['token'], data['wallet']
    ))
    conn.commit()
    conn.close()

    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT type, label, details FROM requisites")
    rows = cursor.fetchall()
    conn.close()

    fiat = "\n".join([f"- {label}: {details}" for (typ, label, details) in rows if typ == "fiat"]) or "Нет реквизитов"
    crypto = "\n".join([f"- {label}: {details}" for (typ, label, details) in rows if typ == "crypto"]) or "Нет реквизитов"

    rec_text = (
        f"📑 <b>Фиатные реквизиты:</b>\n{fiat}\n\n"
        f"📑 <b>Криптовалютные реквизиты:</b>\n{crypto}"
    )

    await call.message.edit_text(
        f"✅ Заявка оформлена!\n\n"
        f"💰 Сумма к оплате: <b>{data['byn']} BYN</b>\n\n"
        f"{rec_text}\n\n"
        f"После оплаты нажмите кнопку ниже.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("💸 Я оплатил", callback_data="paid")
        )
    )

    # Убираем клавиатуру (если осталась)
    await call.message.answer("Отмена сделки невозможна. Не создавайте много пустых сделок, иначе вы будете забанены.", reply_markup=ReplyKeyboardRemove())

@dp.callback_query_handler(text="paid", state=BuyCryptoFSM.confirm_order)
async def paid_with_screenshot_prompt(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("📸 Пожалуйста, отправьте скриншот оплаты сообщением.")
    await BuyCryptoFSM.waiting_for_screenshot.set()

@dp.message_handler(content_types=types.ContentType.PHOTO, state=BuyCryptoFSM.waiting_for_screenshot)
async def handle_screenshot(msg: types.Message, state: FSMContext):
    file_id = msg.photo[-1].file_id
    user_id = msg.from_user.id

    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE orders 
        SET status = 'screenshot_uploaded', details = details || ?
        WHERE id = (
            SELECT id FROM orders 
            WHERE user_id = ? AND type = 'buy' 
            ORDER BY id DESC LIMIT 1
        )
    """, (f"\nСкриншот: {file_id}", user_id))
    conn.commit()
    conn.close()

    await msg.answer("✅ Скриншот получен! Ожидайте подтверждение от оператора.")

    role = get_user_role(user_id)
    await msg.answer("🏠 Вы возвращены в главное меню:", reply_markup=get_main_menu(user_id, role))

    await state.finish()

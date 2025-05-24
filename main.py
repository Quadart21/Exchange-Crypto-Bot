import asyncio
from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher.handler import CancelHandler
from config import dp, bot, logger
from database.db import initialize_db, get_user_role, get_user_username, update_user_username, user_exists, register_user
from keyboards.main_menu import get_main_menu
from handlers.user_handlers_buy import *
from handlers.user_handllers_sell import *
from handlers.admin.operator_handlers import *
from handlers.admin.crypto_wallet import *
from handlers.admin.fiat_wallet import *
from handlers.profile_handlers import *
from handlers.admin.rules_handlers import *
from handlers.user_rules_handlers import *
from handlers.operator_handlers import *
from handlers.admin.operator_crypto import *
from handlers.admin.broadcast import *
from handlers.admin.order_admin import *
from handlers.admin.admin_requisites import *
from handlers.admin.admin_markup import *
from handlers.admin.statistics_handlers import *
import random
from datetime import datetime, timedelta
from aiogram.types import InputFile
from fastapi import FastAPI, Request, HTTPException
import uvicorn
from heleket_api import verify_webhook
import sys
from webhook_handler import router as webhook_router

sys.stdout.reconfigure(encoding='utf-8')

# Новый FastAPI-приложение
app = FastAPI()

app.include_router(webhook_router)


# Словарь для хранения капч и количества попыток
captcha_data = {}
banned_users = {}

# Словарь с описаниями смайлов
EMOJI_DESCRIPTIONS = {  # Описания нарочно с опечаткой, чтобы усложнить автоматический подбор
    "🔥": "огонь (не туши)",  
    "💀": "мертвячок (или просто плохой день)",  
    "👑": "корону (не для Золушки)",  
    "🦸": "супермена (но без плаща)",  
    "🎸": "гитару (рвать струны)",  
    "🤖": "робота (не Алису, честно)",  
    "👽": "пришельца (не зови на ужин)",  
    "🕶️": "очки (чтобы скрыть слезы)",  
    "🧨": "петарду (не в руки)",  
    "🍕": "пиццу (а где моя?)",  
    "🍌": "банан (скользкий тип)",  
    "🍩": "пончик (дырка от бублика)",  
    "🚽": "трон (для размышлений)",  
    "🧻": "рулон (золото 2020)",  
    "🎲": "кубик (не будь змеей)",  
    "🪓": "топор (не для бани)",  
    "🧊": "лёд (Diamond hands)",  
    "🛸": "тарелку (мамкину не предлагать)",  
    "🎮": "дрочку (геймпадную)",  
    "📞": "трубу (алло, это база?)",  
    "💣": "бомбу (не кликай)",  
    "🪑": "стул (для стримов)",  
    "🔫": "водный пистолет (но это не точно)",  
    "🧲": "магнит (для ex не работает)",  
    "🕹️": "джойстик (вставь монетку)",  
    "🎯": "в яблочко (или в дартс)",  
    "🛌": "лежак (работа подождёт)",  
    "🧯": "огнетушитель (на всякий)",  
    "🪨": "камень (ножницы бьют)",  
    "🧸": "мишку (но не того)",  
    "🪣": "ведро (не для краба)",  
    "🛒": "тележку (беги в Ашан)",  
    "📸": "фото (без правок)",  
    "💊": "таблетку (синюю или красную?)",  
    "🧃": "пакет (сок — ротозеям бок)",  
    "🪠": "вантуз (спаситель труб)",  
    "🎈": "шарик (лопни и испугай кота)",  
    "🛟": "круг (спасёт или утопит)",  
    "🧨": "хлопушку (новый год отменяется)",  
    "🪜": "лестницу (в небо или в подвал)",  
    "📯": "рожок (не для музыки)",  
    "🕯️": "свечку (без интернета)"  
}

class BanCheckMiddleware(BaseMiddleware):
    async def on_pre_process_message(self, message: types.Message, data: dict):
        # Проверяем, не забанен ли пользователь
        if is_user_banned(message.from_user.id):
            unban_time = banned_users[message.from_user.id]['unban_time']
            remaining_time = unban_time - datetime.now()
            minutes = int(remaining_time.total_seconds() // 60)
            await message.answer(f"🚫 Вы заблокированы на {minutes} минут за многократные неправильные ответы на капчу.")
            raise CancelHandler()  # Отменяем дальнейшую обработку

    async def on_pre_process_callback_query(self, call: types.CallbackQuery, data: dict):
        # Проверяем, не забанен ли пользователь
        if is_user_banned(call.from_user.id):
            unban_time = banned_users[call.from_user.id]['unban_time']
            remaining_time = unban_time - datetime.now()
            minutes = int(remaining_time.total_seconds() // 60)
            await call.answer(f"🚫 Вы заблокированы на {minutes} минут.", show_alert=True)
            raise CancelHandler()  # Отменяем дальнейшую обработку

async def start_aiogram():
    logger.info("Запуск бота...")
    initialize_db()  # Инициализация базы данных

    # Пропускаем старые сообщения
    await dp.skip_updates()

    # Запускаем polling
    await dp.start_polling(bot)

def generate_captcha():
    # Выбираем 3 случайных смайла из доступных
    available_emojis = list(EMOJI_DESCRIPTIONS.keys())
    captcha_emojis = random.sample(available_emojis, 6)
    correct_answer = captcha_emojis[0]
    
    # Получаем описание для правильного ответа
    description = EMOJI_DESCRIPTIONS[correct_answer]
    question = f"Выберите {description}"
    
    # Перемешиваем варианты ответов
    random.shuffle(captcha_emojis)
    
    return question, captcha_emojis, correct_answer

def is_user_banned(user_id):
    if user_id in banned_users:
        if datetime.now() < banned_users[user_id]['unban_time']:
            return True
        else:
            del banned_users[user_id]
    return False

def setup_middleware(dp):
    middleware = BanCheckMiddleware()
    dp.setup_middleware(middleware)

@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    telegram_id = message.from_user.id
    
    # Генерируем новую капчу
    question, emojis, correct_answer = generate_captcha()
    
    # Сохраняем данные капчи
    captcha_data[telegram_id] = {
        'correct_answer': correct_answer,
        'attempts': 0,
        'question': question
    }
    
    # Создаем клавиатуру с вариантами ответов
    keyboard = types.InlineKeyboardMarkup(row_width=5)
    buttons = [
        types.InlineKeyboardButton(text=emoji, callback_data=f"captcha_{emoji}")
        for emoji in emojis
    ]
    keyboard.add(*buttons)
    
    # Отправляем капчу
    await message.answer(
        "🔒 Пожалуйста, подтвердите, что вы не бот:\n"
        f"{question}",
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda call: call.data.startswith("captcha_"))
async def process_captcha(call: types.CallbackQuery):
    telegram_id = call.from_user.id
    user_answer = call.data.replace("captcha_", "")
    
    # Проверяем, есть ли данные капчи для этого пользователя
    if telegram_id not in captcha_data:
        await call.answer("Время действия капчи истекло. Нажмите /start снова.")
        return
    
    # Получаем данные капчи
    data = captcha_data[telegram_id]
    
    # Проверяем ответ
    if user_answer == data['correct_answer']:
        # Удаляем данные капчи
        del captcha_data[telegram_id]
        
        # Продолжаем стандартный процесс старта
        await successful_start(call.message, call.from_user)
        await call.answer("✅ Капча пройдена успешно!")
    else:
        data['attempts'] += 1
        remaining_attempts = 5 - data['attempts']
        
        if data['attempts'] >= 5:
            # Блокируем пользователя на 30 минут
            unban_time = datetime.now() + timedelta(minutes=30)
            banned_users[telegram_id] = {
                'unban_time': unban_time,
                'attempts': data['attempts']
            }
            del captcha_data[telegram_id]
            
            await call.answer("❌ Вы превысили лимит попыток. Доступ заблокирован на 30 минут.", show_alert=True)
            
            # Логируем блокировку
            logger.warning(f"User {telegram_id} banned for 30 minutes due to failed captcha attempts")
        else:
            # Генерируем новую капчу
            question, emojis, correct_answer = generate_captcha()
            data['correct_answer'] = correct_answer
            data['question'] = question
            
            # Обновляем клавиатуру
            keyboard = types.InlineKeyboardMarkup(row_width=3)
            buttons = [
                types.InlineKeyboardButton(text=emoji, callback_data=f"captcha_{emoji}")
                for emoji in emojis
            ]
            keyboard.add(*buttons)
            
            # Редактируем сообщение с новой капчей
            await call.message.edit_text(
                f"❌ Неверный ответ. Осталось попыток: {remaining_attempts}\n"
                f"{question}",
                reply_markup=keyboard
            )
            await call.answer("Неверный ответ!")


support_link = "https://t.me/bitby_dev"


async def successful_start(message: types.Message, user: types.User):
    """Обработка команды /start для нового или существующего пользователя."""
    telegram_id = user.id
    name = user.first_name
    username = user.username

    print(f"🛠 Обработка команды /start от пользователя {telegram_id}")  # Отладка

    if not user_exists(telegram_id):
        print("❗ Пользователь не найден. Начинаем регистрацию...")
        register_user(telegram_id, name, username)
    else:
        existing_username = get_user_username(telegram_id)
        if username != existing_username:
            print(f"🔄 Обновляем username для пользователя {telegram_id}: "
                  f"{existing_username} → {username}")
            update_user_username(telegram_id, username)

    role = get_user_role(telegram_id)
    print(f"🔍 Роль пользователя: {role}")  # Отладка

    welcome_text = (
        f"👋 Добро пожаловать, {name}!\n\n"
        "🔒 Надежность и безопасность — наш приоритет.\n\n"
        "⚡ С нами вы можете быстро:\n"
        "- Купить криптовалюту по выгодному курсу.\n"
        "- Продать свои активы с минимальными комиссиями.\n\n"
        "💼 Ваши средства под надежной защитой, а поддержка всегда готова помочь!\n\n"
        "Нажмите кнопку в меню, чтобы начать.\n\n"
        f"Если возникнут вопросы — [напишите в поддержку]({support_link})"
    )

    image_path = "img/welcome.jpg"

    try:
        photo = InputFile(image_path)
        await message.answer_photo(
            photo=photo,
            caption=welcome_text,
            reply_markup=get_main_menu(telegram_id, role),
            parse_mode="Markdown"
        )
        print(f"✅ Приветственное сообщение с изображением отправлено "
              f"пользователю {telegram_id}")
    except FileNotFoundError:
        print(f"❌ Изображение {image_path} не найдено. Отправка только текста.")
        await message.answer(
            welcome_text,
            reply_markup=get_main_menu(telegram_id, role),
            parse_mode="Markdown"
        )


@dp.callback_query_handler()
async def debug_callback_query(call: types.CallbackQuery):
    print(f"📥 Получен callback_query: {call.data}")
    await call.answer("Callback получен!")


# Новый роут для приёма Heleket webhook
# Запуск aiogram + fastapi
async def start_bot():
    logger.info("Запуск бота...")
    initialize_db()
    await dp.skip_updates()
    await dp.start_polling(bot)

async def start_webhook_server():
    config = uvicorn.Config(app, host="45.8.147.242", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    setup_middleware(dp)
    await asyncio.gather(
        start_bot(),
        start_webhook_server()
    )

if __name__ == "__main__":
    print("[DEBUG] Бот запускается...")
    import handlers.admin.admin_markup  # 💥 обязательно, иначе хендлеры не работают
    asyncio.run(main())

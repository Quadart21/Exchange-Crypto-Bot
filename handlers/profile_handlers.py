from aiogram import types
from aiogram.dispatcher.filters import Text
from aiogram.types import InputFile
from config import dp, bot
from database.db import get_user_orders, get_user_data
from keyboards.main_menu import profile_menu, get_main_menu


# Команда "Профиль"
@dp.message_handler(lambda message: message.text.strip().lower() == "👤 профиль")
async def profile_handler(message: types.Message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data:
        await message.reply("❌ Ваш профиль не найден. Пожалуйста, зарегистрируйтесь.", reply_markup=profile_menu)
        return

    # Попытка получить аватар пользователя
    photos = await bot.get_user_profile_photos(user_id)
    avatar = None
    if photos.total_count > 0:
        # Берем самое первое фото
        avatar = photos.photos[0][-1]  # Последний вариант (максимальное качество)

    # Формируем текст ответа
    response_text = (
        f"👤 *Профиль*\n\n"
        f"🆔 *ID*: `{user_data[0]}`\n"
        f"👤 *Имя*: {user_data[1]}\n"
    )

    if avatar:
        # Если есть аватар, отправляем фото с текстом
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=avatar.file_id,
            caption=response_text,
            reply_markup=profile_menu,
            parse_mode="Markdown",
        )
    else:
        # Если аватар отсутствует, отправляем только текст
        await message.reply(response_text, reply_markup=profile_menu, parse_mode="Markdown")


# История заявок
@dp.message_handler(Text(equals="История заявок"))
async def order_history_handler(message: types.Message):
    user_id = message.from_user.id
    orders = get_user_orders(user_id)

    if not orders:
        await message.reply("У вас нет заявок.", reply_markup=profile_menu)
        return

    # Формируем текст с заявками
    response_text = "📋 *История заявок:*\n\n"
    for i, order in enumerate(orders[:10], start=1):  # Показываем максимум 10 последних
        # Преобразуем тип заявки
        order_type = "Купить" if order[0].lower() == "buy" else "Продажа" if order[0].lower() == "sell" else "Неизвестно"

        response_text += (
            f"🔹 *Заявка {i}:*\n"
            f"   ▪️ *Тип*: {order_type}\n"
            f"   ▪️ *Сумма*: {order[1]} BYN\n"
            f"   ▪️ *Курс*: {order[2]}\n"
            f"   ▪️ *Итог*: {order[3]} BYN\n"
            f"   ▪️ *Статус*: {order[4]}\n"
            f"   ▪️ *Дата*: {order[5]}\n\n"
        )

    await message.reply(response_text, parse_mode="Markdown", reply_markup=profile_menu)


# Кнопка "Назад"
@dp.message_handler(Text(equals="В главное меню"))
async def back_to_main(message: types.Message):
    await message.reply("🔙 Возвращаемся в главное меню.", reply_markup=get_main_menu(message.from_user.id))

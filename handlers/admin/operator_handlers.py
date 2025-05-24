from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from config import dp
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from database.db import get_operators, delete_operator_by_telegram_id, update_operator, add_operator
from keyboards.main_menu import operator_edit_menu, operator_management_menu, get_main_menu
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types.message import ContentType
from aiogram.utils import executor

# Состояния для добавления оператора
class AddOperatorState(StatesGroup):
    TelegramID = State()
    Name = State()
    WorkHours = State()

# Состояния для редактирования оператора
# Состояния для редактирования оператора
class EditOperatorState(StatesGroup):
    SelectField = State()  # Выбор поля для изменения
    EnterValue = State()   # Ввод нового значения
    EditingName = State()  # Редактирование имени
    EditingWorkHours = State()  # Редактирование рабочих часов


# Состояния для управления изменением статуса оператора
class OperatorStatusState(StatesGroup):
    selecting_operator = State()
    confirming_status_change = State()


# Генерация клавиатуры с операторами
def generate_operator_status_keyboard(operators):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for operator in operators:
        operator_id, name, _, status, _ = operator
        button_text = f"{name} ({status})"
        keyboard.add(KeyboardButton(button_text))
    keyboard.add("Назад")
    return keyboard


# Клавиатура для подтверждения изменения статуса
def confirm_status_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True).add("Да", "Назад")


# Обработчик кнопки "Изменить статус оператора"
@dp.message_handler(text="Изменить статус оператора")
async def change_operator_status_start(message: types.Message):
    operators = get_operators()
    if not operators:
        await message.answer("Список операторов пуст.")
        return

    keyboard = generate_operator_status_keyboard(operators)
    await message.answer("Выберите оператора для изменения статуса:", reply_markup=keyboard)
    await OperatorStatusState.selecting_operator.set()


# Обработка выбора оператора
@dp.message_handler(state=OperatorStatusState.selecting_operator, content_types=ContentType.TEXT)
async def select_operator(message: types.Message, state: FSMContext):
    selected_text = message.text
    if selected_text == "Назад":
        await state.finish()
        await message.answer("Возврат в меню управления операторами.", reply_markup=operator_management_menu())
        return

    operators = get_operators()
    selected_operator = next((op for op in operators if f"{op[1]} ({op[3]})" == selected_text), None)

    if not selected_operator:
        await message.answer("Выбранный оператор не найден. Попробуйте снова.")
        return

    operator_id, name, _, status, _ = selected_operator
    new_status = "inactive" if status == "active" else "active"

    # Сохранение выбранного оператора в состоянии
    await state.update_data(operator_id=operator_id, new_status=new_status)

    await message.answer(
        f"Вы хотите изменить статус оператора {name} с '{status}' на '{new_status}'?",
        reply_markup=confirm_status_keyboard()
    )
    await OperatorStatusState.confirming_status_change.set()


# Подтверждение изменения статуса
@dp.message_handler(state=OperatorStatusState.confirming_status_change, content_types=ContentType.TEXT)
async def confirm_status_change(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await OperatorStatusState.selecting_operator.set()
        operators = get_operators()
        keyboard = generate_operator_status_keyboard(operators)
        await message.answer("Выберите оператора для изменения статуса:", reply_markup=keyboard)
        return

    if message.text != "Да":
        await message.answer("Пожалуйста, подтвердите изменение статуса или отмените действие.")
        return

    # Получение данных из состояния
    data = await state.get_data()
    operator_id = data.get("operator_id")
    new_status = data.get("new_status")

    # Обновление статуса оператора
    update_operator(operator_id, status=new_status)

    await state.finish()
    await message.answer(
        "Статус оператора успешно изменен.",
        reply_markup=operator_management_menu()
    )

# Команда управления операторами
@dp.message_handler(lambda message: message.text == "Управление операторами")
async def manage_operators(message: types.Message):
    await message.reply("Выберите действие:", reply_markup=operator_management_menu())

# Показать список операторов
@dp.message_handler(lambda message: message.text == "Показать операторов")
async def show_operators(message: types.Message):
    operators = get_operators()
    if operators:
        for op in operators:
            operator_info = (
                f"📋 <b>Информация об операторе</b>:\n"
                f"🔹 <b>ID:</b> {op[0]}\n"
                f"👤 <b>Имя:</b> {op[1]}\n"
                f"🆔 <b>Telegram ID:</b> {op[2]}\n"
                f"⚙️ <b>Статус:</b> {'🟢 Активен' if op[3] == 'active' else '🔴 Неактивен'}\n"
                f"⏰ <b>Часы работы:</b> {op[4]}"
            )
            await message.reply(operator_info, parse_mode="HTML")
    else:
        await message.reply("❌ Операторы не найдены.")
# Добавить оператора
@dp.message_handler(lambda message: message.text == "Добавить оператора")
async def add_operator_start(message: types.Message):
    await message.reply("Введите Telegram ID нового оператора:")
    await AddOperatorState.TelegramID.set()

@dp.message_handler(state=AddOperatorState.TelegramID)
async def add_operator_get_name(message: types.Message, state: FSMContext):
    try:
        telegram_id = int(message.text)
        await state.update_data(telegram_id=telegram_id)
        await message.reply("Введите имя нового оператора:")
        await AddOperatorState.Name.set()
    except ValueError:
        await message.reply("Некорректный ID. Попробуйте снова.")

@dp.message_handler(state=AddOperatorState.Name)
async def add_operator_get_work_hours(message: types.Message, state: FSMContext):
    name = message.text
    await state.update_data(name=name)
    await message.reply("Введите часы работы оператора (например: 09:00-18:00):")
    await AddOperatorState.WorkHours.set()

@dp.message_handler(state=AddOperatorState.WorkHours)
async def add_operator_finish(message: types.Message, state: FSMContext):
    work_hours = message.text
    data = await state.get_data()
    telegram_id = data['telegram_id']
    name = data['name']
    try:
        add_operator(telegram_id, name, work_hours)
        await message.reply("Оператор успешно добавлен.", reply_markup=operator_management_menu())
    except Exception as e:
        await message.reply(f"Ошибка при добавлении оператора: {e}", reply_markup=operator_management_menu())
    await state.finish()


# Начало редактирования данных оператора
@dp.message_handler(lambda message: message.text == "Изменить данные оператора")
async def edit_operator_prompt(message: types.Message, state: FSMContext):
    await message.reply("Введите ID оператора, которого хотите изменить:")
    await EditOperatorState.SelectField.set()

@dp.message_handler(state=EditOperatorState.SelectField)
async def select_operator_to_edit(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.reply("ID должен быть числом. Попробуйте снова.")
        return

    operator_id = int(message.text)
    await state.update_data(operator_id=operator_id)
    await message.reply("Выберите, что вы хотите изменить:", reply_markup=operator_edit_menu())
    await EditOperatorState.EnterValue.set()


@dp.message_handler(lambda message: message.text == "Изменить имя", state=EditOperatorState.EnterValue)
async def change_operator_name_start(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        operator_id = data.get("operator_id")
        if not operator_id:
            await message.reply("Сначала выберите оператора, чтобы изменить его данные.")
            return
    await message.reply("Введите новое имя для оператора:")
    await EditOperatorState.EditingName.set()


@dp.message_handler(state=EditOperatorState.EditingName)
async def update_operator_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        operator_id = data.get("operator_id")
    new_name = message.text

    try:
        update_operator(operator_id, name_screen=new_name)
        await message.reply("✅ Имя оператора успешно обновлено.", reply_markup=operator_management_menu())
    except Exception as e:
        await message.reply(f"❌ Ошибка при обновлении имени: {e}")

    await state.finish()

@dp.message_handler(lambda message: message.text == "Изменить рабочие часы", state=EditOperatorState.EnterValue)
async def change_operator_work_hours_start(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        operator_id = data.get("operator_id")
        if not operator_id:
            await message.reply("Сначала выберите оператора, чтобы изменить его данные.")
            return
    await message.reply("Введите новые рабочие часы для оператора (например: 09:00-18:00):")
    await EditOperatorState.EditingWorkHours.set()


@dp.message_handler(state=EditOperatorState.EditingWorkHours)
async def update_operator_work_hours(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        operator_id = data.get("operator_id")
    new_work_hours = message.text

    try:
        update_operator(operator_id, work_hours=new_work_hours)
        await message.reply("✅ Часы работы оператора успешно обновлены.", reply_markup=operator_management_menu())
    except Exception as e:
        await message.reply(f"❌ Ошибка при обновлении часов работы: {e}")

    await state.finish()

@dp.message_handler(state=EditOperatorState.EnterValue)
async def process_field_to_edit(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        operator_id = data.get("operator_id")
        field = data.get("field")

        if field == "status":
            await message.reply("Выберите новый статус оператора:", reply_markup=status_selection_keyboard())
        else:
            await message.reply("Введите новое значение:")

@dp.message_handler(lambda message: message.text in ["🟢 Active", "🔴 Inactive", "❌ Отмена"], state=EditOperatorState.EnterValue)
async def process_status_change(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.reply("Изменение статуса отменено.", reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
        return

    async with state.proxy() as data:
        operator_id = data.get("operator_id")
        new_status = "active" if message.text == "🟢 Active" else "inactive"

        # Обновление данных в базе
        try:
            update_operator(operator_id, status=new_status)
            await message.reply(f"✅ Статус оператора обновлён: {new_status}", reply_markup=types.ReplyKeyboardRemove())
        except Exception as e:
            await message.reply(f"❌ Ошибка при обновлении статуса: {e}", reply_markup=types.ReplyKeyboardRemove())
        finally:
            await state.finish()

# Удалить оператора
@dp.message_handler(lambda message: message.text == "Удалить оператора")
async def delete_operator_prompt(message: types.Message):
    await message.reply("Введите ID оператора, которого нужно удалить:")

@dp.message_handler(lambda message: message.text.isdigit())
async def confirm_delete_operator(message: types.Message):
    telegram_id = int(message.text)
    try:
        success = delete_operator_by_telegram_id(telegram_id)
        if success:
            await message.reply("✅ Оператор успешно удалён.", reply_markup=operator_management_menu())
        else:
            await message.reply("❗ Оператор с указанным Telegram ID не найден.", reply_markup=operator_management_menu())
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}", reply_markup=operator_management_menu())

# Возвращение в главное меню
@dp.message_handler(lambda message: message.text == "Назад")
async def back_to_main_menu(message: types.Message):
    await message.reply("Возврат в главное меню.", reply_markup=get_main_menu())


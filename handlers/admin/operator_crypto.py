from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from config import dp
from database.db import assign_crypto_to_operator, unassign_crypto_from_operator, get_cryptos_by_operator, get_operators
from keyboards.main_menu import get_operator_crypto_keyboard, get_crypto_keyboard, admin_panel_menu, get_operator_keyboard, get_crypto_unassign_keyboard

class CryptoOperatorState(StatesGroup):
    choose_action = State()
    select_operator = State()
    assign_crypto = State()
    select_crypto = State()
    unassign_crypto = State()

@dp.message_handler(lambda message: message.text == "Привязать оператора")
async def operator_crypto_menu(message: types.Message):
    operators = get_operators()  # Получаем список операторов
    if not operators:  # Проверяем, есть ли операторы в базе
        await message.answer("⚠️ В базе данных нет доступных операторов. Добавьте операторов для продолжения.")
        return

    # Предлагаем выбрать оператора
    await message.answer("Выберите оператора для работы с его криптовалютами:", reply_markup=get_operator_keyboard())
    await CryptoOperatorState.select_operator.set()

@dp.message_handler(state=CryptoOperatorState.select_operator)
async def handle_select_operator(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer("Операция отменена.", reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
        return

    try:
        # Извлекаем ID оператора из текста кнопки
        operator_id = int(message.text.split(":")[0])
        await state.update_data(operator_id=operator_id)  # Сохраняем ID оператора в состоянии
        await message.answer(
            "Выберите действие с криптовалютами оператора:",
            reply_markup=get_operator_crypto_keyboard()
        )
        await CryptoOperatorState.choose_action.set()
    except (ValueError, IndexError):
        await message.answer("Введите корректный ID оператора из предложенного списка.")

@dp.message_handler(state=CryptoOperatorState.choose_action)
async def handle_crypto_action(message: types.Message, state: FSMContext):
    data = await state.get_data()
    operator_id = data.get("operator_id")  # Получаем ID выбранного оператора

    if not operator_id:
        await message.answer("Ошибка: оператор не выбран. Сначала выберите оператора.", reply_markup=admin_panel_menu())
        await state.finish()
        return

    if message.text == "Отвязать криптовалюту":
        # Получаем криптовалюты, привязанные к оператору
        cryptos = get_cryptos_by_operator(operator_id)
        if not cryptos:
            await message.answer("У этого оператора нет привязанных криптовалют.", reply_markup=admin_panel_menu())
            await state.finish()
            return

        # Показать клавиатуру с криптовалютами для отвязки
        await message.answer("Выберите криптовалюту, которую хотите отвязать:", reply_markup=get_crypto_unassign_keyboard(operator_id))
        await CryptoOperatorState.unassign_crypto.set()

    elif message.text == "Привязать криптовалюту":
        # Показать доступные криптовалюты для привязки
        await message.answer("Выберите криптовалюту для привязки из списка:", reply_markup=get_crypto_keyboard())
        await CryptoOperatorState.select_crypto.set()

    elif message.text == "Посмотреть привязки":
        # Получаем список привязанных криптовалют
        cryptos = get_cryptos_by_operator(operator_id)
        if not cryptos:
            await message.answer("У этого оператора нет привязанных криптовалют.", reply_markup=admin_panel_menu())
        else:
            crypto_list = "\n".join([f"{crypto[0]}: {crypto[1]}" for crypto in cryptos])
            await message.answer(f"Привязанные криптовалюты:\n{crypto_list}", reply_markup=admin_panel_menu())
        await state.finish()

    elif message.text == "Отмена":
        await message.answer("Операция отменена.", reply_markup=admin_panel_menu())
        await state.finish()

    else:
        await message.answer(
            "Неверный выбор. Пожалуйста, выберите одно из предложенных действий или вернитесь в главное меню.",
            reply_markup=get_operator_crypto_keyboard()
        )

@dp.message_handler(state=CryptoOperatorState.select_crypto)
async def handle_crypto_selection(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer("Операция отменена.", reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
        return

    try:
        crypto_id = int(message.text.split(":")[0])
        data = await state.get_data()
        operator_id = data.get("operator_id")

        if operator_id is None:
            await message.answer("Ошибка: ID оператора не найден. Начните заново.")
            await state.finish()
            return

        if assign_crypto_to_operator(operator_id, crypto_id):
            await message.answer(
                f"Криптовалюта с ID {crypto_id} успешно привязана к оператору {operator_id}.",
                reply_markup=admin_panel_menu()
            )
        else:
            await message.answer("Ошибка при привязке. Попробуйте снова.", reply_markup=admin_panel_menu())
    except ValueError:
        await message.answer("Выберите криптовалюту из предложенного списка.")
    finally:
        await state.finish()

@dp.message_handler(state=CryptoOperatorState.unassign_crypto)
async def unassign_crypto_handler(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer("Операция отменена.", reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
        return

    try:
        crypto_id = int(message.text.split(":")[0])

        if unassign_crypto_from_operator(crypto_id):
            await message.answer(
                f"Криптовалюта с ID {crypto_id} успешно отвязана.",
                reply_markup=admin_panel_menu()
            )
        else:
            await message.answer(
                "Ошибка при отвязке. Проверьте данные и попробуйте снова.",
                reply_markup=admin_panel_menu()
            )
    except (ValueError, IndexError):
        await message.answer("Выберите криптовалюту из предложенного списка.")
    finally:
        await state.finish()

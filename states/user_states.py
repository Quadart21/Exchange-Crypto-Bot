from aiogram.dispatcher.filters.state import State, StatesGroup

# Состояния для покупки и продажи
class ExchangeStates(StatesGroup):
    choose_currency = State()  # Выбор валюты
    enter_amount = State()  # Ввод суммы
    confirm = State()  # Подтверждение данных
    enter_details = State()  # Ввод реквизитов

class ProfileStates(StatesGroup):
    edit_details = State()  # Редактирование реквизитов

class ContactStates(StatesGroup):
    send_message = State()  # Отправка сообщения оператору

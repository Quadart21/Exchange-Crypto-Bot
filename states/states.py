from aiogram.dispatcher.filters.state import State, StatesGroup

class BuyCryptoStates(StatesGroup):
    select_currency = State()
    input_amount = State()
    confirm_amount = State()
    input_wallet = State()
    confirm_order = State()

class SellCryptoStates(StatesGroup):
    select_currency = State()
    input_crypto_amount = State()
    confirm_crypto_amount = State()
    input_requisites = State()
    confirm_order = State()

class RulesStates(StatesGroup):
    waiting_for_rules = State()

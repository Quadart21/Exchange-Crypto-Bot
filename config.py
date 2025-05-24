from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import logging

# Настройка логирования
logging.basicConfig(
    filename='logs/bot.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


# Токен бота
BOT_TOKEN = "7850744684:AAFyveu4x5d883UXWgQRW4TBdjRI0fu89Ow"
CHANNEL_ID = -1002422011698  # Замените на ваш ID группы
ADMIN_ID = "8058997213"  # Используем список чисел
NOWNODES_API_KEY = "f28bec03-0b48-4d22-a88e-ba3249d2f3ab"
HELEKET_API_URL = "https://api.heleket.com/v1/payment"
HELEKET_MERCHANT_ID = "f62d2ac5-addd-4d28-8ac9-c7ebe89d6ef3"
HELEKET_API_KEY = "75ccYNzG0DDsSGxm7qLSjsZyjYZXSXGv0IYSwf7bkssEsnODg9EchjKMa7qH3kEACxFjhGAKbgFT6XCE6vjgdw5iCH1XfVybChIZ5Xcf5KLqsPc2Vp4Vo9uaGtbgMLxX"
# Инициализация бота и хранилища FSM
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# Наценки на покупку
MARKUP_BUY_USD = 10.0
MARKUP_BUY_OTHER = 10.0

# Наценки на продажу
MARKUP_SELL_USD = -5.0
MARKUP_SELL_OTHER = -5.0

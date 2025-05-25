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
BOT_TOKEN = ""
ADMIN_ID = ""  # Используем список чисел
NOWNODES_API_KEY = ""
HELEKET_API_URL = "https://api.heleket.com/v1/payment"
HELEKET_MERCHANT_ID = ""
HELEKET_API_KEY = ""
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

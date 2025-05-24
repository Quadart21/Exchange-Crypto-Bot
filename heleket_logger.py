# heleket_logger.py
import logging

# Настройка логгера для Heleket
logger = logging.getLogger("heleket_logger")
logger.setLevel(logging.DEBUG)

# Создаём обработчик записи в файл
file_handler = logging.FileHandler("heleket_errors.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)

# Формат логов
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)

# Добавляем обработчик к логгеру
logger.addHandler(file_handler)

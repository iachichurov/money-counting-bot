import os
import logging
from dotenv import load_dotenv

from telegram.ext import Application
from bot.handlers import register_handlers
from bot.db import init_db

# Включаем логирование, чтобы видеть, что происходит и где что отвалилось.
# Без логов ты как слепой котенок в машинном отделении.
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    """Запускает всю нашу шарманку."""
    # Загружаем переменные окружения из файла .env
    # Первым делом, блядь! Чтобы токен был доступен.
    load_dotenv()

    # Инициализируем базу данных. Создаем таблицы, если их нет.
    # Это создаст файл базы данных, если его еще нет, и подготовит структуру
    # Важно вызвать перед стартом бота, чтобы избежать ошибок при первом запуске
    init_db()

    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        logger.critical("Пиздец! Токен не найден. Проверь файл .env")
        return

    # Создаем объект приложения
    application = Application.builder().token(TOKEN).build()

    # Регистрируем все наши хендлеры (обработчики команд)
    # Сама функция будет жить в handlers.py
    register_handlers(application)

    # Запускаем бота. Он начинает слушать телегу.
    logger.info("Бот запущен и готов разъебывать...")
    application.run_polling()

if __name__ == "__main__":
    main()
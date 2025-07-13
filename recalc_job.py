import logging
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Мы импортируем функции из нашего модуля bot
from bot.db import get_all_active_users, get_spent_for_period, update_user_balance

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def run_recalculations():
    """
    Главная функция. Проходит по всем пользователям и выполняет пересчет,
    если для них наступил новый день.
    """
    logger.info("Запуск задачи пересчета балансов...")
    active_users = get_all_active_users()

    for user in active_users:
        user_id = user["user_id"]

        try:
            user_tz = ZoneInfo(user["timezone"])
        except ZoneInfoNotFoundError:
            logger.warning(f"Неверная таймзона '{user['timezone']}' для пользователя {user_id}. Пропускаем.")
            continue

        # Определяем текущее время для пользователя
        now_local = datetime.now(user_tz)
        today_local_date_str = now_local.strftime('%Y-%m-%d')

        # Проверяем, не делали ли мы уже пересчет для этого пользователя СЕГОДНЯ
        if user["last_recalc_date"] == today_local_date_str:
            # logger.info(f"Для пользователя {user_id} пересчет сегодня уже был. Пропускаем.")
            continue

        # Если время пользователя перевалило за полночь, пора считать
        if now_local.hour >= 0:
            logger.info(f"Для пользователя {user_id} наступил новый день. Начинаем пересчет...")

            # Определяем начало и конец ВЧЕРАШНЕГО дня для пользователя
            yesterday_local = now_local - timedelta(days=1)
            start_of_yesterday_local = yesterday_local.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_yesterday_local = start_of_yesterday_local + timedelta(days=1)

            # Конвертируем в UTC для запроса в базу
            start_utc = start_of_yesterday_local.astimezone(ZoneInfo("UTC")).isoformat()
            end_utc = end_of_yesterday_local.astimezone(ZoneInfo("UTC")).isoformat()

            # Считаем, сколько было потрачено за вчера
            spent_yesterday = get_spent_for_period(user_id, start_utc, end_utc)

            # Вычисляем новый накопленный баланс
            base_norm = user["daily_norm"]
            old_balance = user["accumulated_balance"]

            # Формула: (что было доступно вчера) - (что потратил вчера)
            new_balance = (base_norm + old_balance) - spent_yesterday

            # Обновляем данные в базе
            update_user_balance(user_id, new_balance, today_local_date_str)

    logger.info("Задача пересчета балансов завершена.")


if __name__ == "__main__":
    run_recalculations()
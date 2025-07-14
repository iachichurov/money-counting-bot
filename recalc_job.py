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
    Главная функция. Проходит по всем пользователям и выполняет пересчет
    для КАЖДОГО пропущенного дня.
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

        # --- НОВАЯ, НАДЕЖНАЯ ЛОГИКА С ЦИКЛОМ ---

        # Берем дату последнего пересчета из базы
        last_recalc_date = date.fromisoformat(user["last_recalc_date"])
        # Определяем сегодняшний день в таймзоне пользователя
        today_local_date = datetime.now(user_tz).date()

        # Если последний пересчет уже был сегодня, пропускаем
        if last_recalc_date >= today_local_date:
            continue

        logger.info(f"Для пользователя {user_id} найдены пропущенные дни. Начинаем пересчет с {last_recalc_date}...")

        # Начинаем цикл с дня, следующего за последним пересчетом
        day_to_process = last_recalc_date
        current_balance = user["accumulated_balance"]

        # Цикл работает, пока мы не дойдем до сегодняшнего дня
        while day_to_process < today_local_date:
            # Определяем начало и конец дня, который мы обрабатываем
            start_of_day_local = datetime.combine(day_to_process, datetime.min.time(), tzinfo=user_tz)
            end_of_day_local = start_of_day_local + timedelta(days=1)

            start_utc = start_of_day_local.astimezone(ZoneInfo("UTC")).isoformat()
            end_utc = end_of_day_local.astimezone(ZoneInfo("UTC")).isoformat()

            # Считаем траты за этот конкретный день
            spent_on_day = get_spent_for_period(user_id, start_utc, end_utc)

            base_norm = user["daily_norm"]

            # Вычисляем новый баланс на КОНЕЦ обрабатываемого дня
            current_balance = (base_norm + current_balance) - spent_on_day

            logger.info(
                f"  - День {day_to_process}: потрачено {spent_on_day}, "
                f"новый баланс на конец дня: {current_balance}"
            )

            # Переходим к следующему дню
            day_to_process += timedelta(days=1)

        # После того, как все пропущенные дни обработаны,
        # обновляем баланс в базе и ставим дату последнего пересчета на СЕГОДНЯ.
        update_user_balance(user_id, current_balance, today_local_date.isoformat())

    logger.info("Задача пересчета балансов завершена.")


if __name__ == "__main__":
    run_recalculations()
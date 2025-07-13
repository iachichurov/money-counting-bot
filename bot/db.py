import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)

DB_NAME = "data/budget_bot.db"


@contextmanager
def get_db_connection():
    """
    Устанавливает соединение с базой и ГАРАНТИРОВАННО закрывает его.
    Теперь это контекстный менеджер.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        # Отдаем соединение наружу для работы в блоке 'with'
        yield conn
    finally:
        # Этот блок выполнится ВСЕГДА, даже если внутри 'with' произошла ошибка.
        conn.close()
        # logger.debug("Соединение с базой данных закрыто") # Можно включить для отладки


def init_db():
    """Создает таблицы, если их еще нет. Теперь с 'with'."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                daily_norm REAL NOT NULL,
                reset_day INTEGER NOT NULL,
                timezone TEXT NOT NULL,
                accumulated_balance REAL NOT NULL DEFAULT 0,
                last_recalc_date TEXT,
                is_active BOOLEAN NOT NULL DEFAULT 1
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                created_at_utc TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        conn.commit()
    logger.info("База данных инициализирована по финальной схеме v3.0.")


def get_user(user_id: int):
    """Ищет пользователя в базе по его ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
    return user


def create_user(user_id: int, daily_norm: float, timezone: str):
    """Создает нового пользователя в базе данных."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        reset_day = date.today().day
        try:
            user_tz = ZoneInfo(timezone)
            last_recalc_date = datetime.now(user_tz).strftime('%Y-%m-%d')
        except ZoneInfoNotFoundError:
            logger.warning(f"Неверная таймзона {timezone} для юзера {user_id}. Ставим по МСК.")
            last_recalc_date = datetime.now(ZoneInfo("Europe/Moscow")).strftime('%Y-%m-%d')

        cursor.execute(
            """
            INSERT INTO users (user_id, daily_norm, reset_day, timezone, last_recalc_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, daily_norm, reset_day, timezone, last_recalc_date)
        )
        conn.commit()
    logger.info(f"В базу добавлен новый пользователь: {user_id} с датой пересчета {last_recalc_date}")


def add_transaction(user_id: int, amount: float):
    """Добавляет новую транзакцию в базу."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        created_at_utc = datetime.now(ZoneInfo("UTC")).isoformat()
        cursor.execute(
            "INSERT INTO transactions (user_id, amount, created_at_utc) VALUES (?, ?, ?)",
            (user_id, amount, created_at_utc)
        )
        conn.commit()
    logger.info(f"Добавлена транзакция {amount} для пользователя {user_id}")


def get_spent_today(user_id: int) -> float:
    """Считает, сколько пользователь потратил за СВОЙ сегодняшний день."""
    user = get_user(user_id)
    if not user: return 0.0

    try:
        user_tz = ZoneInfo(user["timezone"])
    except ZoneInfoNotFoundError:
        user_tz = ZoneInfo("Europe/Moscow")

    now_local = datetime.now(user_tz)
    start_of_day_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day_local = start_of_day_local + timedelta(days=1)

    start_of_day_utc = start_of_day_local.astimezone(ZoneInfo("UTC")).isoformat()
    end_of_day_utc = end_of_day_local.astimezone(ZoneInfo("UTC")).isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT SUM(amount)
            FROM transactions
            WHERE user_id = ?
              AND created_at_utc >= ?
              AND created_at_utc < ?
            """,
            (user_id, start_of_day_utc, end_of_day_utc)
        )
        result = cursor.fetchone()

    return result[0] if result and result[0] is not None else 0.0


def get_all_active_users():
    """Возвращает список всех активных пользователей для пересчета."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE is_active = 1")
        users = cursor.fetchall()
    return users


def get_spent_for_period(user_id: int, start_utc: str, end_utc: str) -> float:
    """Считает траты за произвольный период времени (в UTC)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT SUM(amount)
            FROM transactions
            WHERE user_id = ?
              AND created_at_utc >= ?
              AND created_at_utc < ?
            """,
            (user_id, start_utc, end_utc)
        )
        result = cursor.fetchone()
    return result[0] if result and result[0] is not None else 0.0


def update_user_balance(user_id: int, new_balance: float, recalc_date: str):
    """Обновляет накопленный баланс и дату последнего пересчета."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET accumulated_balance = ?, last_recalc_date = ? WHERE user_id = ?",
            (new_balance, recalc_date, user_id)
        )
        conn.commit()
    logger.info(f"Баланс пользователя {user_id} обновлен на {new_balance}")

def update_daily_norm(user_id: int, new_norm: float):
    """Обновляет дневную норму для пользователя."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET daily_norm = ? WHERE user_id = ?",
            (new_norm, user_id)
        )
        conn.commit()
    logger.info(f"Дневная норма для пользователя {user_id} обновлена на {new_norm}")

from .db import get_user, get_spent_today


def calculate_status(user_id: int) -> dict:
    """
    Собирает всю инфу о состоянии пользователя и возвращает в виде словаря.
    """
    user = get_user(user_id)
    if not user:
        return None

    spent_today = get_spent_today(user_id)

    base_norm = user['daily_norm']
    balance = user['accumulated_balance']

    available_today = base_norm + balance
    remaining_today = available_today - spent_today

    return {
        "base_norm": base_norm,
        "balance": balance,
        "available_today": available_today,
        "spent_today": spent_today,
        "remaining_today": remaining_today,
    }
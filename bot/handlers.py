import logging
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Импортируем новую клавиатуру
from .keyboards import (
    TIMEZONE_KEYBOARD, TIMEZONE_CALLBACK_PREFIX,
    CONFIRM_DELETE_KEYBOARD, CONFIRM_DELETE_CALLBACK_PREFIX
)
# Импортируем новую функцию из db.py
from .db import create_user, get_user, add_transaction, update_daily_norm, delete_user
from .logic import calculate_status

logger = logging.getLogger(__name__)

# Определяем состояния для ТРЕХ разных диалогов.
GET_NORM, GET_TIMEZONE = 0, 1
CHANGING_NORM = 2
CONFIRM_DELETION = 3


# --- ДИАЛОГ РЕГИСТРАЦИИ ---
async def start(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    db_user = get_user(user.id)
    if db_user:
        await update.message.reply_text("Ты уже в системе, вояка. Вноси траты или жми /status.")
        return ConversationHandler.END
    await update.message.reply_text(
        f"Здарова, {user.first_name}. Вижу тебя впервые.\nДавай определим твою дневную норму трат. Сколько рублей в день ты хочешь тратить? Просто отправь число.")
    return GET_NORM


# ... (код get_norm, get_timezone остается без изменений) ...
async def get_norm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        daily_norm = float(update.message.text)
        if daily_norm <= 0:
            raise ValueError
    except (ValueError, TypeError):
        await update.message.reply_text("Это не похоже на положительное число. А ну-ка, введи нормально.")
        return GET_NORM
    context.user_data['daily_norm'] = daily_norm
    await update.message.reply_text("Принято. Теперь выбери свой часовой пояс...", reply_markup=TIMEZONE_KEYBOARD)
    return GET_TIMEZONE


async def get_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    timezone_str = query.data.split(":")[1]
    daily_norm = context.user_data.get('daily_norm')
    user = update.effective_user
    create_user(user_id=user.id, daily_norm=daily_norm, timezone=timezone_str)
    context.user_data.clear()
    await query.edit_message_text(
        text=f"Отлично! Твоя норма: {daily_norm} руб/день.\nТвой часовой пояс: {timezone_str}.\nТеперь просто присылай мне числа, когда что-то потратишь.")
    return ConversationHandler.END


# --- ОБЩАЯ ФУНКЦИЯ ОТМЕНЫ ДЛЯ ВСЕХ ДИАЛОГОВ ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END


# --- ДИАЛОГ ДЛЯ /settings ---
async def settings_entry(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (код settings_entry и receive_new_norm остается без изменений) ...
    user_id = update.effective_user.id
    db_user = get_user(user_id)
    if not db_user:
        await update.message.reply_text("Сначала зарегистрируйся через /start, умник.")
        return ConversationHandler.END
    try:
        user_tz = ZoneInfo(db_user["timezone"])
    except ZoneInfoNotFoundError:
        user_tz = ZoneInfo("Europe/Moscow")
    today_day_number = datetime.now(user_tz).day
    reset_day = db_user["reset_day"]
    if today_day_number == reset_day:
        norm_str = str(db_user['daily_norm']).replace('.', ',')
        await update.message.reply_text(
            f"Твоя текущая норма: `{norm_str}` руб\\.\n"
            "Сегодня твой день сброса! Введи новую дневную норму, если хочешь ее поменять\\.",
            parse_mode='MarkdownV2'
        )
        return CHANGING_NORM
    else:
        await update.message.reply_text(
            f"Сегодня не твой день\\. Смена нормы доступна только *{reset_day}* числа каждого месяца\\.\n"
            "Приходи позже, салага\\.",
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END


async def receive_new_norm(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        new_norm = float(update.message.text.strip().replace(',', '.'))
        if new_norm <= 0:
            raise ValueError
    except (ValueError, TypeError):
        await update.message.reply_text("Это не похоже на сумму. Введи нормальное число или жми /cancel\\.")
        return CHANGING_NORM
    user_id = update.effective_user.id
    update_daily_norm(user_id, new_norm)
    norm_str = str(new_norm).replace('.', ',')
    await update.message.reply_text(f"Принято\\. Твоя новая дневная норма: `{norm_str}` руб\\.",
                                    parse_mode='MarkdownV2')
    return ConversationHandler.END


# --- НОВЫЙ ДИАЛОГ ДЛЯ /delete_me ---

async def delete_me_entry(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    """Входная точка для диалога удаления. Спрашивает подтверждение."""
    user_id = update.effective_user.id
    if not get_user(user_id):
        await update.message.reply_text("Тебя и так нет в базе, чего удалять-то?")
        return ConversationHandler.END

    await update.message.reply_text(
        "Ты уверен, что хочешь *ПОЛНОСТЬЮ* удалить все свои данные?\n"
        "Это действие необратимо. Весь твой накопленный баланс и история трат будут стерты к хуям.",
        reply_markup=CONFIRM_DELETE_KEYBOARD,
        parse_mode='Markdown'  # Используем обычный Markdown, он проще
    )
    return CONFIRM_DELETION


async def confirm_deletion(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает нажатие кнопок 'Да' или 'Нет'."""
    query = update.callback_query
    await query.answer()

    # Получаем 'yes' или 'no' из callback_data
    choice = query.data.split(":")[1]

    if choice == "yes":
        user_id = update.effective_user.id
        delete_user(user_id)
        await query.edit_message_text("Все твои данные уничтожены. Можешь начать с чистого листа через /start.")
    else:
        await query.edit_message_text("Правильное решение. Удаление отменено.")

    return ConversationHandler.END


# --- ОБРАБОТЧИКИ ВНЕ ДИАЛОГОВ ---
async def status_handler(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    # ... (код status_handler и transaction_handler остается без изменений) ...
    user_id = update.effective_user.id
    user_status = calculate_status(user_id)
    if not user_status:
        await update.message.reply_text("Сначала пройди регистрацию через /start.")
        return
    norm_str = str(round(user_status['base_norm'], 2)).replace('.', ',')
    balance_str = str(round(user_status['balance'], 2)).replace('.', ',')
    available_str = str(round(user_status['available_today'], 2)).replace('.', ',')
    spent_str = str(round(user_status['spent_today'], 2)).replace('.', ',')
    remaining_str = str(round(user_status['remaining_today'], 2)).replace('.', ',')
    text = (
        f"📊 *Твоя сводка на сегодня:*\n\n"
        f"Базовая норма: `{norm_str}`\n"
        f"Накоплено/долг: `{balance_str}`\n\n"
        f"✅ *Доступно сегодня:* `{available_str}`\n"
        f" потрачено: `{spent_str}`\n"
        f" остаток: `{remaining_str}`"
    )
    await update.message.reply_text(text, parse_mode='MarkdownV2')


async def transaction_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not get_user(user_id):
        await update.message.reply_text("Не понимаю. Если хочешь начать, жми /start.")
        return
    try:
        amount = float(update.message.text.strip().replace(',', '.'))
        if amount <= 0: raise ValueError
    except (ValueError, TypeError):
        await update.message.reply_text("Это не похоже на сумму\\. Просто пришли число, например `150` или `123\\.45`",
                                        parse_mode='MarkdownV2')
        return
    add_transaction(user_id, amount)
    await status_handler(update, context)


# --- РЕГИСТРАЦИЯ ВСЕХ ОБРАБОТЧИКОВ ---
def register_handlers(application: Application):
    """Регистрирует все обработчики в приложении."""

    registration_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GET_NORM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_norm)],
            GET_TIMEZONE: [CallbackQueryHandler(get_timezone, pattern=f"^{TIMEZONE_CALLBACK_PREFIX}:")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=600
    )

    settings_conv = ConversationHandler(
        entry_points=[CommandHandler("settings", settings_entry)],
        states={
            CHANGING_NORM: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_norm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=300
    )

    # Новый диалог удаления
    delete_conv = ConversationHandler(
        entry_points=[CommandHandler("delete_me", delete_me_entry)],
        states={
            CONFIRM_DELETION: [CallbackQueryHandler(confirm_deletion, pattern=f"^{CONFIRM_DELETE_CALLBACK_PREFIX}:")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=60
    )

    application.add_handler(registration_conv)
    application.add_handler(settings_conv)
    application.add_handler(delete_conv)  # Добавляем новый диалог

    application.add_handler(CommandHandler("status", status_handler))
    application.add_handler(
        MessageHandler(filters.Regex(r'^\d+([.,]\d{1,2})?$') & ~filters.COMMAND, transaction_handler))

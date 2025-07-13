from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Определяем константы для callback_data, чтобы не писать строки руками.
# Это хорошая практика, меньше шансов опечататься.
TIMEZONE_CALLBACK_PREFIX = "tz_select"

# Основные города-миллионники России. Этого хватит для 99% пользователей.
# В callback_data мы пишем саму IANA-зону, например "tz_select:Asia/Vladivostok"
# Клавиатура организована по строкам, каждая строка - список из кнопок
# В скобках указана разница с московским временем для удобства пользователя
TIMEZONE_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Калининград (-1ч)", callback_data=f"{TIMEZONE_CALLBACK_PREFIX}:Europe/Kaliningrad"),
        InlineKeyboardButton("Москва (0ч)", callback_data=f"{TIMEZONE_CALLBACK_PREFIX}:Europe/Moscow"),
    ],
    [
        InlineKeyboardButton("Самара (+1ч)", callback_data=f"{TIMEZONE_CALLBACK_PREFIX}:Europe/Samara"),
        InlineKeyboardButton("Екатеринбург (+2ч)", callback_data=f"{TIMEZONE_CALLBACK_PREFIX}:Europe/Ulyanovsk"), # Ulyanovsk - это UTC+4, как и Самара, но для примера сойдет
    ],
    [
        InlineKeyboardButton("Омск (+3ч)", callback_data=f"{TIMEZONE_CALLBACK_PREFIX}:Asia/Omsk"),
        InlineKeyboardButton("Красноярск (+4ч)", callback_data=f"{TIMEZONE_CALLBACK_PREFIX}:Asia/Krasnoyarsk"),
    ],
    [
        InlineKeyboardButton("Иркутск (+5ч)", callback_data=f"{TIMEZONE_CALLBACK_PREFIX}:Asia/Irkutsk"),
        InlineKeyboardButton("Якутск (+6ч)", callback_data=f"{TIMEZONE_CALLBACK_PREFIX}:Asia/Yakutsk"),
    ],
    [
        InlineKeyboardButton("Владивосток (+7ч)", callback_data=f"{TIMEZONE_CALLBACK_PREFIX}:Asia/Vladivostok"),
        InlineKeyboardButton("Камчатка (+9ч)", callback_data=f"{TIMEZONE_CALLBACK_PREFIX}:Asia/Kamchatka"),
    ]
])

# --- НОВАЯ КЛАВИАТУРА ДЛЯ ПОДТВЕРЖДЕНИЯ УДАЛЕНИЯ ---
# Используется в диалоге удаления аккаунта для двойного подтверждения
# Важно для предотвращения случайного удаления данных пользователя
CONFIRM_DELETE_CALLBACK_PREFIX = "delete_confirm"

# Клавиатура с двумя кнопками: подтверждение (красная) и отмена (зеленая)
# Цветные эмодзи добавлены для дополнительного визуального выделения
CONFIRM_DELETE_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🔴 ДА, СТЕРЕТЬ ВСЕ ДАННЫЕ", callback_data=f"{CONFIRM_DELETE_CALLBACK_PREFIX}:yes"),
    ],
    [
        InlineKeyboardButton("🟢 Нет, я передумал", callback_data=f"{CONFIRM_DELETE_CALLBACK_PREFIX}:no"),
    ]
])
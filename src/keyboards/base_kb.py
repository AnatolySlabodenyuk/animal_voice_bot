from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from config_data.config import Config, load_config
from lexicon.buttons_enum import ButtonsEnum

config: Config = load_config()

webapp_url = config.tg_bot.webapp_url

# ------- Создаем клавиатуру через ReplyKeyboardBuilder -------
# Создаем кнопки
button_restart: KeyboardButton = KeyboardButton(text=ButtonsEnum.RESTART_BUTTON.value)

voice_category_choose: KeyboardButton = KeyboardButton(
    text=ButtonsEnum.VOICE_CATEGORY_CHOOSE_BUTTON.value
)

button_guess_sound_web: KeyboardButton = KeyboardButton(
    text=ButtonsEnum.GUESS_SOUND_WEB_BUTTON.value,
    web_app=WebAppInfo(
        url=f"{webapp_url}/game"
    ),  # Placeholder - REPLACE WITH YOUR HTTPS URL
)

button_help: KeyboardButton = KeyboardButton(text=ButtonsEnum.HELP_BUTTON.value)

button_search_in_web: KeyboardButton = KeyboardButton(
    text=ButtonsEnum.SEARCH_IN_WEB.value
)

# Инициализируем билдер для клавиатуры с кнопками:
base_kb_builder = ReplyKeyboardBuilder()

# Добавляем кнопки в билдер с аргументом width=1 (количество кнопок в ряду)
base_kb_builder.row(
    button_restart,
    voice_category_choose,

    button_guess_sound_web,
    button_help,
    button_search_in_web,
    width=1,
)

# Создаем клавиатуру с кнопками:
base_kb: ReplyKeyboardMarkup = base_kb_builder.as_markup(
    # one_time_keyboard=True,
    resize_keyboard=True
)

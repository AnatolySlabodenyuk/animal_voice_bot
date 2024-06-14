from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from lexicon.buttons_enum import InlineButtons, CallbackData

# ------- Создаем клавиатуру через ReplyKeyboardBuilder -------

# Создаем инлайн-кнопки с выбором животных
inline_button_cat: InlineKeyboardButton = InlineKeyboardButton(
    text=InlineButtons.CAT.value,
    callback_data=CallbackData.INLINE_BUTTON_CAT_PRESSED.value
)

inline_button_dog: InlineKeyboardButton = InlineKeyboardButton(
    text=InlineButtons.DOG.value,
    callback_data=CallbackData.INLINE_BUTTON_DOG_PRESSED.value
)

inline_button_сhewbacca: InlineKeyboardButton = InlineKeyboardButton(
    text=InlineButtons.CHEWBACCA.value,
    callback_data=CallbackData.INLINE_BUTTON_CHEWBACCA_PRESSED.value
)

# Инициализируем билдер для клавиатуры с инлайн-кнопками:
inline_kb_builder = InlineKeyboardBuilder()


# Добавляем кнопки в билдер с аргументом width=1 (количество кнопок в ряду)
inline_kb_builder.row(inline_button_cat, inline_button_dog,
                      inline_button_сhewbacca, width=1)

# Создаем клавиатуру с кнопками:
inline_kb: InlineKeyboardMarkup = inline_kb_builder.as_markup(
    # one_time_keyboard=True,
    resize_keyboard=True
)


# TODO
# Функция для генерации инлайн-клавиатур "на лету"
def create_inline_kb(width: int,
                     *args: str,
                     **kwargs: str) -> InlineKeyboardMarkup:
    # Инициализируем билдер
    kb_builder = InlineKeyboardBuilder()
    # Инициализируем список для кнопок
    buttons: list[InlineKeyboardButton] = []

    # Заполняем список кнопками из аргументов args и kwargs
    if args:
        for button in args:
            buttons.append(InlineKeyboardButton(
                text=button.value,
                callback_data=CallbackData[f'inline_button_{button.name}_pressed'].value))
    if kwargs:
        for button, callback in kwargs.items():
            buttons.append(InlineKeyboardButton(
                text=button.value,
                callback_data=callback.value))

    # Распаковываем список с кнопками в билдер методом row c параметром width
    kb_builder.row(*buttons, width=width)

    # Возвращаем объект инлайн-клавиатуры
    return kb_builder.as_markup()

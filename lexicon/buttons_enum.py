import enum


class ButtonsEnum(enum.Enum):
    RESTART_BUTTON = "♻️ Перезапустить бота"
    ANIMAL_CHOOSE_BUTTON = "🙈 Выбрать животное"
    AUDIO_UPLOAD = "🎧 Загрузить звук"
    HELP_BUTTON = "📄 Инструкция"


class InlineButtonsEnum(enum.Enum):
    CAT = "🐈 Кот"
    DOG = "🐶 Собака"
    CHEWBACCA = "🚀 Чубакка"


class CallbackDataEnum(enum.Enum):
    INLINE_BUTTON_CAT_PRESSED = "inline_button_cat_pressed"
    INLINE_BUTTON_DOG_PRESSED = "inline_button_dog_pressed"
    INLINE_BUTTON_CHEWBACCA_PRESSED = "inline_button_сhewbacca_pressed"

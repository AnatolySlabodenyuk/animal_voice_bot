import enum


class BaseCommands(enum.Enum):
    START = "Привет!\n\nЯ эхо-бот для демонстрации работы роутеров!\n\n"
    HELP = "Здесь будет инструкция..."
    ANIMAL_CHOOSE_BUTTON = "Это список животных. Выбери любое!"
    OTHER_ANSWER = "Извини, увы, это сообщение мне непонятно..."

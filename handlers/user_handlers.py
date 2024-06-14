from aiogram import F, Router, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command, CommandStart
from keyboards.base_kb import base_kb
from keyboards.inline_kb import inline_kb
from lexicon.base_commands_enum import BaseCommands
from lexicon.buttons_enum import Buttons, InlineButtons, CallbackData
from database.database import create_table, get_file_id_from_table, add_audio_to_table


# Инициализируем роутер уровня модуля
router = Router()


# Этот хэндлер срабатывает на команду /start
@router.message(CommandStart())
async def process_start_command(message: Message):
    await message.answer(
        text=BaseCommands.START.value,
        reply_markup=base_kb
    )


# Этот хэндлер срабатывает на кнопку restart_button
@router.message(F.text == Buttons.RESTART_BUTTON.value)
async def process_restart_button(message: Message):
    await message.answer(
        text=BaseCommands.START.value,
        reply_markup=base_kb
    )


# Этот хэндлер срабатывает на команду /help
@router.message(Command(commands="help"))
async def process_help_command(message: Message):
    await message.answer(
        text=BaseCommands.HELP.value,
        reply_markup=base_kb
    )


# Этот хэндлер срабатывает на кнопку help_button
@router.message(F.text == Buttons.HELP_BUTTON.value)
async def process_help_button(message: Message):
    await message.answer(
        text=BaseCommands.HELP.value,
        reply_markup=base_kb
    )


# Этот хэндлер срабатывает на кнопку выбрать животное
@router.message(F.text == Buttons.ANIMAL_CHOOSE_BUTTON.value)
async def process_animal_choose_button(message: Message):
    await message.answer(
        text=BaseCommands.ANIMAL_CHOOSE_BUTTON.value,
        reply_markup=inline_kb
    )


# Универсальная функция для обработки нажатий на инлайн-кнопки с животными
async def process_button_press(callback: CallbackQuery, animal_in_table: str, animal_name: str, audio_path: str):
    await create_table()
    file_record = await get_file_id_from_table(animal_in_table)
    if file_record is None:
        await callback.answer(f"Так говорит Мистер {animal_name}")
        audio = FSInputFile(audio_path)
        message = await callback.message.answer_audio(audio=audio)
        file_id = message.audio.file_id
        await add_audio_to_table(
            file_name=animal_in_table,
            file_id=file_id
        )
        # await callback.message.answer(f"File Id : {file_id}")
    else:
        file_id = file_record[0]
        await callback.answer(f"Так говорит Мистер {animal_name}")
        await callback.message.answer_audio(audio=file_id)
        # await callback.message.answer(f"File Id : {file_id}")


# Этот хэндлер будет срабатывать на нажатие инлайн-кнопки с животным Кошка
@router.callback_query(F.data == CallbackData.INLINE_BUTTON_CAT_PRESSED.value)
async def process_button_cat_press(callback: CallbackQuery):
    await process_button_press(
        callback=callback,
        animal_in_table=InlineButtons.CAT.name,
        animal_name=InlineButtons.CAT.value,
        audio_path='database/sounds/cat.mp3'
    )


# Этот хэндлер будет срабатывать на нажатие инлайн-кнопки с животным Собака
@router.callback_query(F.data == CallbackData.INLINE_BUTTON_DOG_PRESSED.value)
async def process_button_dog_press(callback: CallbackQuery):
    await process_button_press(
        callback=callback,
        animal_in_table=InlineButtons.DOG.name,
        animal_name=InlineButtons.DOG.value,
        audio_path='database/sounds/dog.mp3'
    )


# Этот хэндлер будет срабатывать на нажатие инлайн-кнопки с животным Чубакка
@router.callback_query(F.data == CallbackData.INLINE_BUTTON_CHEWBACCA_PRESSED.value)
async def process_button_сhewbacca_press(callback: CallbackQuery):
    await process_button_press(
        callback=callback,
        animal_in_table=InlineButtons.CHEWBACCA.name,
        animal_name=InlineButtons.CHEWBACCA.value,
        audio_path='database/sounds/chewbacca.mp3'
    )

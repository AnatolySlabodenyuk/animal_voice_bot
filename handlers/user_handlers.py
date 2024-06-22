from aiogram import F, Router, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command, CommandStart
from keyboards.base_kb import base_kb
from keyboards.inline_kb import inline_kb
from keyboards.inline_kb_new import AnimalsCallbackFactory, create_inline_kb
from lexicon.base_commands_enum import BaseCommandsEnum
from lexicon.buttons_enum import ButtonsEnum, InlineButtonsEnum, CallbackDataEnum
from database.database import create_table, get_file_id_from_table, add_audio_to_table, get_button_ids, get_file_name_from_table

# Инициализируем роутер уровня модуля
router = Router()


# Этот хэндлер срабатывает на команду /start
@router.message(CommandStart())
async def process_start_command(message: Message):
    await message.answer(
        text=BaseCommandsEnum.START.value,
        reply_markup=base_kb
    )


# Этот хэндлер срабатывает на кнопку restart_button
@router.message(F.text == ButtonsEnum.RESTART_BUTTON.value)
async def process_restart_button(message: Message):
    await message.answer(
        text=BaseCommandsEnum.START.value,
        reply_markup=base_kb
    )


# Этот хэндлер срабатывает на команду /help
@router.message(Command(commands="help"))
async def process_help_command(message: Message):
    await message.answer(
        text=BaseCommandsEnum.HELP.value,
        reply_markup=base_kb
    )


# Этот хэндлер срабатывает на кнопку help_button
@router.message(F.text == ButtonsEnum.HELP_BUTTON.value)
async def process_help_button(message: Message):
    await message.answer(
        text=BaseCommandsEnum.HELP.value,
        reply_markup=base_kb
    )


# Этот хэндлер срабатывает на кнопку загрузить звук
@router.message(F.text == ButtonsEnum.AUDIO_UPLOAD.value)
async def process_audio_upload_button(message: Message):
    await message.answer(text=BaseCommandsEnum.AUDIO_UPLOAD.value)


# State for handling name input
class Form:
    state_file_id = None


# Этот хэндлер срабатывает загрузку аудио
@router.message(F.audio)
async def process_upload_audio(message: Message):
    file_id = message.audio.file_id
    await message.reply("Пожалуйста, введите название животного.")
    Form.state_file_id = file_id


# Этот хэндлер срабатывает на задание имени для аудио
@router.message(lambda message: Form.state_file_id is not None)
async def process_set_file_name(message: Message):
    file_name = message.text
    file_id = Form.state_file_id
    await add_audio_to_table(file_name, file_id)
    Form.state_file_id = None
    await message.answer(
        text=f"Аудиофайл сохранен с именем {file_name}!",
        reply_markup=base_kb
    )


# Этот хэндлер срабатывает на кнопку выбрать животное
# @router.message(F.text == Buttons.ANIMAL_CHOOSE_BUTTON.value)
# async def process_animal_choose_button(message: Message):
#     await message.answer(
#         text=BaseCommands.ANIMAL_CHOOSE_BUTTON.value,
#         reply_markup=inline_kb
#     )


# Этот хэндлер срабатывает на кнопку выбрать животное
@router.message(F.text == ButtonsEnum.ANIMAL_CHOOSE_BUTTON.value)
async def process_animal_choose_button(message: Message):
    button_ids = await get_button_ids()
    inline_kb = await create_inline_kb(width=1, button_ids=button_ids)
    await message.answer(
        text=BaseCommandsEnum.ANIMAL_CHOOSE_BUTTON.value,
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


# Этот хэндлер будет срабатывать на нажатие любой инлайн кнопки
# и отправлять в чат форматированный ответ с данными из callback_data
@router.callback_query(AnimalsCallbackFactory.filter())
async def process_animal_press(callback: CallbackQuery,
                               callback_data: AnimalsCallbackFactory):
    await process_button_press(
        callback=callback,
        animal_in_table=await get_file_name_from_table(callback_data.button_id),
        animal_name=await get_file_name_from_table(callback_data.button_id),
        audio_path=f'database/sounds/{await get_file_name_from_table(callback_data.button_id)}.mp3'
    )


# # Этот хэндлер будет срабатывать на нажатие инлайн-кнопки с животным Кошка
# @router.callback_query(F.data == CallbackDataEnum.INLINE_BUTTON_CAT_PRESSED.value)
# async def process_button_cat_press(callback: CallbackQuery):
#     await process_button_press(
#         callback=callback,
#         animal_in_table=InlineButtonsEnum.CAT.name,
#         animal_name=InlineButtonsEnum.CAT.value,
#         audio_path='database/sounds/cat.mp3'
#     )


# # Этот хэндлер будет срабатывать на нажатие инлайн-кнопки с животным Собака
# @router.callback_query(F.data == CallbackDataEnum.INLINE_BUTTON_DOG_PRESSED.value)
# async def process_button_dog_press(callback: CallbackQuery):
#     await process_button_press(
#         callback=callback,
#         animal_in_table=InlineButtonsEnum.DOG.name,
#         animal_name=InlineButtonsEnum.DOG.value,
#         audio_path='database/sounds/dog.mp3'
#     )


# # Этот хэндлер будет срабатывать на нажатие инлайн-кнопки с животным Чубакка
# @router.callback_query(F.data == CallbackDataEnum.INLINE_BUTTON_CHEWBACCA_PRESSED.value)
# async def process_button_сhewbacca_press(callback: CallbackQuery):
#     await process_button_press(
#         callback=callback,
#         animal_in_table=InlineButtonsEnum.CHEWBACCA.name,
#         animal_name=InlineButtonsEnum.CHEWBACCA.value,
#         audio_path='database/sounds/chewbacca.mp3'
#     )

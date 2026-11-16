import asyncio
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from config_data.config import load_config
from database.database import (
    add_audio_to_table, add_image_to_table, get_all_users,
    get_user_stats_page,
)
from keyboards.rich_menu import (
    RichMenuScreen, back_button, build_rich_menu, callback_button,
    remove_legacy_reply_keyboard,
)
from lexicon.base_commands_enum import BaseCommandsEnum
from lexicon.buttons_enum import ButtonsEnum
from lexicon.voice_types_enum import VoiceCategoryEnum

router = Router()
config = load_config()
ADMIN_USER_ID = config.tg_bot.admin_user_id
feedback_message = config.tg_bot.feedback_message

ADMIN_MENU = "admin:menu"
ADMIN_AUDIO = "admin:audio"
ADMIN_IMAGE = "admin:image"
ADMIN_STATS = "admin:stats"
ADMIN_FEEDBACK = "admin:feedback"
ADMIN_AUDIO_CATEGORY = "admin:audio:category:"
ADMIN_IMAGE_CATEGORY = "admin:image:category:"


class UploadState(StatesGroup):
    waiting_for_audio_file_id = State()
    waiting_for_audio_name = State()
    waiting_for_audio_category = State()
    waiting_for_image_file_id = State()
    waiting_for_image_name = State()
    waiting_for_image_category = State()


def is_admin(event: Message | CallbackQuery) -> bool:
    return bool(event.from_user and event.from_user.id == int(ADMIN_USER_ID))


async def reject_non_admin(event: Message | CallbackQuery) -> bool:
    if is_admin(event):
        return False
    if isinstance(event, CallbackQuery):
        await event.answer(BaseCommandsEnum.ACCESS_DENIED.value, show_alert=True)
    else:
        await event.answer(BaseCommandsEnum.ACCESS_DENIED.value)
    return True


async def answer_screen(message: Message, screen: RichMenuScreen) -> Message:
    await message.answer("Меню открыто ниже.", reply_markup=remove_legacy_reply_keyboard())
    return await message.answer_rich(rich_message=build_rich_menu(screen))


async def edit_screen(callback: CallbackQuery, screen: RichMenuScreen) -> None:
    if isinstance(callback.message, Message):
        await callback.message.edit_text(rich_message=build_rich_menu(screen))


async def edit_upload_screen(message: Message, state: FSMContext, screen: RichMenuScreen):
    menu_id = (await state.get_data())["upload_menu_id"]
    await message.bot.edit_message_text(
        chat_id=message.chat.id, message_id=menu_id, rich_message=build_rich_menu(screen),
    )


def admin_screen() -> RichMenuScreen:
    return RichMenuScreen(
        BaseCommandsEnum.ADMIN.value,
        (
            (callback_button(ButtonsEnum.AUDIO_UPLOAD.value, ADMIN_AUDIO, style="primary"),),
            (callback_button(ButtonsEnum.IMAGE_UPLOAD.value, ADMIN_IMAGE, style="primary"),),
            (callback_button(ButtonsEnum.GET_STATS.value, ADMIN_STATS),),
            (callback_button(ButtonsEnum.SEND_FEEDBACK.value, ADMIN_FEEDBACK, style="danger"),),
        ),
    )


def category_screen(kind: str) -> RichMenuScreen:
    prefix = ADMIN_AUDIO_CATEGORY if kind == "audio" else ADMIN_IMAGE_CATEGORY
    return RichMenuScreen(
        BaseCommandsEnum.SET_FILE_CATEGORY.value,
        (
            tuple(callback_button(item.value, f"{prefix}{item.name}") for item in VoiceCategoryEnum),
            (back_button(ADMIN_MENU),),
        ),
    )


@router.message(Command(commands="admin"))
async def process_admin_command(message: Message):
    if not await reject_non_admin(message):
        await answer_screen(message, admin_screen())


@router.callback_query(F.data == ADMIN_MENU)
async def process_admin_menu(callback: CallbackQuery, state: FSMContext):
    if not await reject_non_admin(callback):
        await callback.answer()
        await state.clear()
        await edit_screen(callback, admin_screen())


async def start_upload(message: Message, state: FSMContext, kind: str) -> None:
    if await reject_non_admin(message):
        return
    state_value = UploadState.waiting_for_audio_file_id if kind == "audio" else UploadState.waiting_for_image_file_id
    prompt = BaseCommandsEnum.AUDIO_UPLOAD.value if kind == "audio" else BaseCommandsEnum.IMAGE_UPLOAD.value
    await state.set_state(state_value)
    menu = await answer_screen(message, RichMenuScreen(prompt, ((back_button(ADMIN_MENU),),)))
    await state.update_data(upload_menu_id=menu.message_id)


@router.message(F.text == ButtonsEnum.AUDIO_UPLOAD.value)
async def process_audio_upload_button(message: Message, state: FSMContext):
    await start_upload(message, state, "audio")


@router.message(F.text == ButtonsEnum.IMAGE_UPLOAD.value)
async def process_image_upload_button(message: Message, state: FSMContext):
    await start_upload(message, state, "image")


@router.callback_query(F.data.in_({ADMIN_AUDIO, ADMIN_IMAGE}))
async def process_upload_menu(callback: CallbackQuery, state: FSMContext):
    if await reject_non_admin(callback):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await state.clear()
    await state.update_data(upload_menu_id=callback.message.message_id)
    kind = "audio" if callback.data == ADMIN_AUDIO else "image"
    state_value = UploadState.waiting_for_audio_file_id if kind == "audio" else UploadState.waiting_for_image_file_id
    prompt = BaseCommandsEnum.AUDIO_UPLOAD.value if kind == "audio" else BaseCommandsEnum.IMAGE_UPLOAD.value
    await state.set_state(state_value)
    await callback.answer()
    await edit_screen(callback, RichMenuScreen(prompt, ((back_button(ADMIN_MENU),),)))


@router.message(UploadState.waiting_for_audio_file_id, F.audio)
async def process_upload_audio_new(message: Message, state: FSMContext):
    if await reject_non_admin(message):
        return
    await state.update_data(waiting_for_audio_file_id=message.audio.file_id)
    await state.set_state(UploadState.waiting_for_audio_name)
    await edit_upload_screen(message, state, RichMenuScreen(BaseCommandsEnum.SET_AUDIO_FILE_NAME.value, ((back_button(ADMIN_MENU),),)))


@router.message(UploadState.waiting_for_image_file_id, F.photo)
async def process_upload_image_new(message: Message, state: FSMContext):
    if await reject_non_admin(message):
        return
    await state.update_data(waiting_for_image_file_id=message.photo[-1].file_id)
    await state.set_state(UploadState.waiting_for_image_name)
    await edit_upload_screen(message, state, RichMenuScreen(BaseCommandsEnum.SET_IMAGE_FILE_NAME.value, ((back_button(ADMIN_MENU),),)))


@router.message(UploadState.waiting_for_audio_name, F.text.func(lambda text: bool(text.strip())))
async def audio_name_chosen(message: Message, state: FSMContext):
    if await reject_non_admin(message):
        return
    await state.update_data(waiting_for_audio_name=message.text or "")
    await state.set_state(UploadState.waiting_for_audio_category)
    await edit_upload_screen(message, state, category_screen("audio"))


@router.message(UploadState.waiting_for_image_name, F.text.func(lambda text: bool(text.strip())))
async def image_name_chosen(message: Message, state: FSMContext):
    if await reject_non_admin(message):
        return
    await state.update_data(waiting_for_image_name=message.text or "")
    await state.set_state(UploadState.waiting_for_image_category)
    await edit_upload_screen(message, state, category_screen("image"))


async def save_upload(callback: CallbackQuery, state: FSMContext, kind: str) -> None:
    if await reject_non_admin(callback):
        return
    prefix = ADMIN_AUDIO_CATEGORY if kind == "audio" else ADMIN_IMAGE_CATEGORY
    category_name = (callback.data or "").removeprefix(prefix)
    try:
        category = VoiceCategoryEnum[category_name].value
    except KeyError:
        await callback.answer(BaseCommandsEnum.SOMETHING_WRONG.value, show_alert=True)
        return
    values = await state.get_data()
    file_key = f"waiting_for_{kind}_file_id"
    name_key = f"waiting_for_{kind}_name"
    expected_state = getattr(UploadState, f"waiting_for_{kind}_category").state
    if (not isinstance(callback.message, Message)
            or callback.message.message_id != values.get("upload_menu_id")
            or await state.get_state() != expected_state
            or not values.get(file_key) or not values.get(name_key)):
        await callback.answer("Загрузку начните заново.", show_alert=True)
        return
    if kind == "audio":
        await add_audio_to_table(values.get(name_key, ""), category, values[file_key])
        item = "Аудиофайл"
    else:
        await add_image_to_table(values.get(name_key, ""), category, values[file_key])
        item = "Картинка"
    await state.clear()
    await callback.answer()
    await edit_screen(callback, RichMenuScreen(
        f"{item} сохранен с именем {values.get(name_key, '')}\nи категорией {category}!",
        ((back_button(ADMIN_MENU),),),
    ))


@router.callback_query(F.data.startswith(ADMIN_AUDIO_CATEGORY))
async def audio_category_chosen(callback: CallbackQuery, state: FSMContext):
    await save_upload(callback, state, "audio")


@router.callback_query(F.data.startswith(ADMIN_IMAGE_CATEGORY))
async def image_category_chosen(callback: CallbackQuery, state: FSMContext):
    await save_upload(callback, state, "image")


async def stats_screen(sort: str = "active", page: int = 0) -> RichMenuScreen:
    total, active, page, pages, users = await get_user_stats_page(sort, page)
    lines = [
        "Статистика пользователей",
        f"Всего в базе: {total} · За последние 7 дней: {active}",
        f"Страница {page + 1} из {pages} · Время МСК",
        "",
    ]
    for user_id, username, count, last in users:
        timestamp = "—"
        if last:
            utc = datetime.fromisoformat(last).replace(tzinfo=timezone.utc)
            timestamp = utc.astimezone(timezone(timedelta(hours=3))).strftime("%d.%m.%Y %H:%M")
        label = f"@{username}" if username else f"ID {user_id}"
        lines.append(f"{label} · {count} запр. · {timestamp}")
    if not users:
        lines.append("Пользователей пока нет.")
    modes = (("active", "Последние активные"), ("requests", "Топ по запросам"))
    rows = [tuple(
        callback_button(("✓ " if mode == sort else "") + label, f"admin:stats:{mode}:0")
        for mode, label in modes
    )]
    navigation = []
    if page:
        navigation.append(callback_button("← Предыдущая", f"admin:stats:{sort}:{page - 1}"))
    if page + 1 < pages:
        navigation.append(callback_button("Следующая →", f"admin:stats:{sort}:{page + 1}"))
    if navigation:
        rows.append(tuple(navigation))
    rows.append((callback_button("Обновить", f"admin:stats:{sort}:{page}"), back_button(ADMIN_MENU)))
    return RichMenuScreen("\n".join(lines), rows)


@router.message(F.text == ButtonsEnum.GET_STATS.value)
async def process_stats_command(message: Message):
    if not await reject_non_admin(message):
        await answer_screen(message, await stats_screen())


@router.callback_query((F.data == ADMIN_STATS) | F.data.regexp(r"^admin:stats:(active|requests):[0-9]{1,8}$"))
async def process_stats_menu(callback: CallbackQuery):
    if await reject_non_admin(callback):
        return
    await callback.answer()
    sort, page = ("active", "0") if callback.data == ADMIN_STATS else callback.data.split(":")[2:]
    try:
        await edit_screen(callback, await stats_screen(sort, int(page)))
    except TelegramBadRequest as error:
        if "message is not modified" not in error.message.lower():
            raise


async def send_feedback(bot, actor: Message | CallbackQuery) -> tuple[int, int]:
    users = await get_all_users()
    success_count = 0
    error_count = 0
    for user_id, _username in users:
        try:
            await bot.send_message(chat_id=user_id, text=feedback_message)
            success_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            error_count += 1
    return success_count, error_count


def feedback_screen(success_count: int, error_count: int) -> RichMenuScreen:
    return RichMenuScreen(
        f"{BaseCommandsEnum.FEEDBACK_SENT.value}\n✅ Успешно отправлено: {success_count}\n❌ Ошибок: {error_count}",
        ((back_button(ADMIN_MENU),),),
    )


@router.message(F.text == ButtonsEnum.SEND_FEEDBACK.value)
async def process_send_feedback_button(message: Message):
    if not await reject_non_admin(message):
        await answer_screen(message, feedback_screen(*await send_feedback(message.bot, message)))


@router.callback_query(F.data == ADMIN_FEEDBACK)
async def process_send_feedback_menu(callback: CallbackQuery):
    if not await reject_non_admin(callback):
        await callback.answer()
        await edit_screen(callback, feedback_screen(*await send_feedback(callback.bot, callback)))

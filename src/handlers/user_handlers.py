from hashlib import blake2s

import logging
import secrets
import time
from dataclasses import asdict
from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ChatAction, ChatType
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardRemove,
    WebAppInfo,
)

from database.database import (
    get_audio_file_id_from_table,
    get_audio_file_name_from_table,
    get_image_file_id_from_table,
    increment_user_request_count,
)
from database.web_sound_cache import WebSoundCache
from keyboards.web_sound_kb import WebSoundCallback, create_web_sound_kb
from lexicon.web_search_enum import WebSearchText
from services.web_sound_search import SoundSearchError, WebSound, WebSoundSearch
from config_data.config import load_config
from keyboards.rich_menu import RichMenuButton, RichMenuScreen, back_button, build_rich_menu
from keyboards.voice_inline_kb import (
    VoiceNamesCallbackFactory,
    VoiceTypesCallbackFactory,
    create_voice_category_inline_kb,
)
from lexicon.base_commands_enum import BaseCommandsEnum
from lexicon.buttons_enum import ButtonsEnum
from lexicon.voice_types_enum import VoiceCategoryEnum

router = Router()

logger = logging.getLogger(__name__)
WEB_SEARCH_RESULT_TTL = 30 * 60


class SearchInNetState(StatesGroup):
    waiting_for_key_word = State()


ROOT_BUTTONS = (
    (ButtonsEnum.RESTART_BUTTON, "home", "danger", "4970142833605345805", "🔄"),
    (ButtonsEnum.VOICE_CATEGORY_CHOOSE_BUTTON, "catalog", "primary", "5472317238851673400", "🗂️"),
    (ButtonsEnum.GUESS_SOUND_WEB_BUTTON, "game", "success", "5213430392798851273", "🎮"),
    (ButtonsEnum.HELP_BUTTON, "help", None, "5334882760735598374", "ℹ️"),
    (ButtonsEnum.SEARCH_IN_WEB, "search", None, "5231012545799666522", "🔎"),
)
PAGE_SIZE = 8
CATEGORY_TITLES = {
    VoiceCategoryEnum.animals.value: BaseCommandsEnum.CHOOSE_ANIMAL.value,
    VoiceCategoryEnum.transport.value: BaseCommandsEnum.CHOOSE_TRANSPORT.value,
    VoiceCategoryEnum.objects.value: BaseCommandsEnum.CHOOSE_OBJECT.value,
}


def home_screen(message: Message) -> RichMenuScreen:
    rows = []
    for label, action, style, emoji_id, fallback in ROOT_BUTTONS:
        if action == "game" and message.chat.type != ChatType.PRIVATE:
            continue
        web_app = None
        if action == "game":
            url = load_config().tg_bot.webapp_url.rstrip("/")
            web_app = WebAppInfo(url=f"{url}/game")
        rows.append([RichMenuButton(
            text=label.value, style=style,
            custom_emoji_id=emoji_id, emoji_fallback=fallback,
            callback_data=None if web_app else f"menu:{action}",
            web_app=web_app,
        )])
    return RichMenuScreen("Привет! Выбери звук из каталога или найди его в сети.", rows)


def with_back(text: str, rows=None, parent="home") -> RichMenuScreen:
    return RichMenuScreen(text, [*(rows or []), [back_button(f"menu:{parent}")]])


async def catalog_screen() -> RichMenuScreen:
    keyboard = await create_voice_category_inline_kb()
    return with_back("🗂 Выбери категорию", [
        [RichMenuButton(text=button.text, callback_data=button.callback_data)]
        for row in keyboard.inline_keyboard for button in row
    ])


async def send_menu(message: Message, screen: RichMenuScreen):
    await message.answer("Меню открыто ниже.", reply_markup=ReplyKeyboardRemove(remove_keyboard=True))
    return await message.answer_rich(rich_message=build_rich_menu(screen))


@router.message(CommandStart())
@router.message(F.text == ButtonsEnum.RESTART_BUTTON.value)
async def process_start_command(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user:
        await increment_user_request_count(message.from_user.id, message.from_user.username or "")
    await send_menu(message, home_screen(message))


def help_screen() -> RichMenuScreen:
    return with_back(
        "Выбери категорию, чтобы послушать звуки из каталога. "
        "Для поиска введи название звука. Игру «Угадай звук» можно открыть из главного меню."
    )


@router.message(Command(commands="help"))
@router.message(F.text == ButtonsEnum.HELP_BUTTON.value)
async def process_help_command(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user:
        await increment_user_request_count(message.from_user.id, message.from_user.username or "")
    await send_menu(message, help_screen())


@router.message(F.text == ButtonsEnum.VOICE_CATEGORY_CHOOSE_BUTTON.value)
async def process_voice_category_choose_button(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user:
        await increment_user_request_count(message.from_user.id, message.from_user.username or "")
    await send_menu(message, await catalog_screen())


@router.callback_query(F.data.in_({"menu:home", "menu:catalog", "menu:help", "menu:search", "help:catalog"}))
async def navigate_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    await increment_user_request_count(callback.from_user.id, callback.from_user.username or "")
    await state.clear()
    if callback.data == "menu:home":
        screen = home_screen(callback.message)
    elif callback.data == "menu:help":
        screen = help_screen()
    elif callback.data == "menu:search":
        screen = with_back("🔍 Какой звук хочешь найти?")
        await state.set_state(SearchInNetState.waiting_for_key_word)
    else:
        screen = await catalog_screen()
    await edit_menu(callback.message, screen)


async def edit_menu(message: Message, screen: RichMenuScreen):
    try:
        await message.edit_text(rich_message=build_rich_menu(screen))
    except TelegramBadRequest as error:
        if "message is not modified" not in error.message.lower():
            raise


@router.callback_query(VoiceTypesCallbackFactory.filter())
async def inline_products_button_press(callback: CallbackQuery, callback_data: VoiceTypesCallbackFactory):
    category = callback_data.voice_type
    if category not in CATEGORY_TITLES:
        await callback.answer(BaseCommandsEnum.SOMETHING_WRONG.value)
        return
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    await increment_user_request_count(callback.from_user.id, callback.from_user.username or "")
    await show_category(callback.message, category, 0)


def sound_key(name: str) -> str:
    return blake2s(name.encode(), digest_size=12).hexdigest()


def category_screen(category: str, names: list[str], page: int) -> RichMenuScreen:
    pages = max(1, (len(names) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, pages - 1)
    index = list(CATEGORY_TITLES).index(category)
    rows = [
        [RichMenuButton(text=name, callback_data=f"sound:{index}:{sound_key(name)}")]
        for name in names[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    ]
    navigation = []
    if page:
        navigation.append(RichMenuButton("← Предыдущая", callback_data=f"page:{index}:{page-1}"))
    if page + 1 < pages:
        navigation.append(RichMenuButton("Следующая →", callback_data=f"page:{index}:{page+1}"))
    if navigation:
        rows.append(navigation)
    title = CATEGORY_TITLES[category] if names else "В этой категории пока нет звуков."
    rows.append([RichMenuButton(ButtonsEnum.VOICE_CATEGORY_CHOOSE_BUTTON.value, callback_data="menu:catalog")])
    return RichMenuScreen(title, rows)


async def catalog_names(category: str) -> list[str]:
    return sorted(set(await get_audio_file_name_from_table(category=category)),
                  key=lambda name: (name.casefold(), name))


async def show_category(message: Message, category: str, page: int):
    await edit_menu(message, category_screen(category, await catalog_names(category), page))


@router.callback_query(F.data.regexp(r"^page:[0-2]:[0-9]{1,8}$"))
async def navigate_category_page(callback: CallbackQuery):
    await callback.answer()
    if isinstance(callback.message, Message):
        _, index, page = callback.data.split(":")
        await show_category(callback.message, list(CATEGORY_TITLES)[int(index)], int(page))


@router.callback_query(F.data.regexp(r"^sound:[0-2]:[0-9a-f]{24}$"))
async def play_catalog_sound(callback: CallbackQuery):
    _, index, key = callback.data.split(":")
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    category = list(CATEGORY_TITLES)[int(index)]
    names = await catalog_names(category)
    position = next((i for i, name in enumerate(names) if sound_key(name) == key), None)
    if position is None:
        await callback.answer("Звук больше недоступен")
        return
    await increment_user_request_count(callback.from_user.id, callback.from_user.username or "")
    actions = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Другой звук", callback_data=f"photo-page:{index}:{position // PAGE_SIZE}"),
        InlineKeyboardButton(text="Главное меню", callback_data="photo-home"),
    ]])
    await get_audio_file(callback, names[position], actions)


@router.callback_query(F.data.regexp(r"^photo-page:[0-2]:[0-9]{1,8}$") | (F.data == "photo-home"))
async def navigate_from_photo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    await state.clear()
    if callback.data == "photo-home":
        screen = home_screen(callback.message)
    else:
        _, index, page = callback.data.split(":")
        category = list(CATEGORY_TITLES)[int(index)]
        screen = category_screen(category, await catalog_names(category), int(page))
    await callback.message.answer_rich(rich_message=build_rich_menu(screen))


async def get_audio_file(callback: CallbackQuery, voice_name: str, actions: InlineKeyboardMarkup | None = None):
    """
    Универсальная функция для обработки нажатий на инлайн-кнопки с животными
    """
    audio_file_id = await get_audio_file_id_from_table(voice_name)
    image_file_id = await get_image_file_id_from_table(voice_name)
    await callback.answer(f"Так звучит {voice_name}"[:200])
    if callback.message and audio_file_id:
        await callback.message.bot.send_chat_action(
            chat_id=callback.message.chat.id, action=ChatAction.UPLOAD_VOICE
        )
        await callback.message.answer_audio(audio=audio_file_id, reply_markup=None if image_file_id else actions)
        if image_file_id:
            await callback.message.answer_photo(photo=image_file_id, reply_markup=actions)


@router.callback_query(VoiceNamesCallbackFactory.filter())
async def process_voice_button_press(
        callback: CallbackQuery, callback_data: VoiceNamesCallbackFactory
):
    """
    Этот хэндлер будет срабатывать на нажатие любой инлайн кнопки
    и отправлять в чат форматированный ответ с данными из callback_data
    """
    if callback.from_user:
        await increment_user_request_count(
            callback.from_user.id, callback.from_user.username or ""
        )
    await get_audio_file(
        callback=callback,
        voice_name=callback_data.voice_name,
    )


@router.message(F.text == ButtonsEnum.SEARCH_IN_WEB.value)
async def process_search_in_web_button(message: Message, state: FSMContext):
    """
    Этот хэндлер срабатывает на кнопку найти в интернете
    """
    if message.from_user:
        await increment_user_request_count(
            message.from_user.id, message.from_user.username or ""
        )
    await state.clear()
    await send_menu(message, with_back("🔍 Какой звук хочешь найти?"))
    await state.set_state(SearchInNetState.waiting_for_key_word)


@router.message(SearchInNetState.waiting_for_key_word)
async def search_audio(
    message: Message, state: FSMContext, web_sound_search: WebSoundSearch,
):
    """List search results; download audio only after the user selects it."""
    query = (message.text or "").strip()
    if not query:
        await message.answer(WebSearchText.INVALID_QUERY.value)
        return
    if len(query) > 200:
        await message.answer(WebSearchText.QUERY_TOO_LONG.value)
        return
    # Register before any database/network await, which can overlap a new search.
    await state.clear()
    token = secrets.token_hex(6)
    await state.update_data(web_search_token=token)
    if message.from_user:
        await increment_user_request_count(
            message.from_user.id, message.from_user.username or ""
        )
    if (await state.get_data()).get("web_search_token") != token:
        return
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    result = await web_sound_search.search(query)
    # A newer search can start while this HTTP request is still in flight.
    if (await state.get_data()).get("web_search_token") != token:
        return
    if not result.sounds:
        await state.clear()
        text = WebSearchText.UNAVAILABLE if result.failed_sources else WebSearchText.NOT_FOUND
        await message.answer_rich(rich_message=build_rich_menu(with_back(text.value, parent="search")))
        return
    await state.update_data(
        web_search_token=token,
        web_search_results=[asdict(sound) for sound in result.sounds],
        web_search_expires=time.time() + WEB_SEARCH_RESULT_TTL,
    )
    text = WebSearchText.CHOOSE_SOUND.value
    if result.failed_sources:
        text = WebSearchText.PARTIAL_RESULTS.value + "\n\n" + text
    await send_web_results(message, data_sounds=result.sounds, token=token, text=text)


async def send_web_results(message: Message, data_sounds: list[WebSound], token: str, text: str):
    attribution = [
        f"{sound.title} — {sound.author or sound.source} · {sound.license}\n{sound.page_url}"
        for sound in data_sounds if sound.license
    ]
    if attribution:
        text += "\n\n" + "\n".join(attribution)
    markup = create_web_sound_kb(data_sounds, token)
    rows = [[RichMenuButton(text=button.text, callback_data=button.callback_data)
             for button in row] for row in markup.inline_keyboard]
    await message.answer_rich(rich_message=build_rich_menu(with_back(text, rows, parent="search")))


@router.callback_query(F.data.regexp(r"^web-back:[0-9a-f]{12}$"))
async def return_to_web_results(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    token = callback.data.split(":", 1)[1]
    if (not isinstance(callback.message, Message)
            or data.get("web_search_token") != token
            or data.get("web_search_expires", 0) <= time.time()
            or not data.get("web_search_results")):
        await callback.answer(WebSearchText.EXPIRED.value, show_alert=True)
        return
    await callback.answer()
    await send_web_results(
        callback.message, [WebSound(**sound) for sound in data["web_search_results"]],
        token, WebSearchText.CHOOSE_SOUND.value,
    )


@router.callback_query(WebSoundCallback.filter())
async def send_web_sound(
    callback: CallbackQuery, callback_data: WebSoundCallback,
    state: FSMContext, web_sound_search: WebSoundSearch,
    web_sound_cache: WebSoundCache,
):
    data = await state.get_data()
    sounds = data.get("web_search_results", [])
    if not isinstance(callback.message, Message):
        await callback.answer(WebSearchText.EXPIRED.value, show_alert=True)
        return
    if (data.get("web_search_token") != callback_data.token
            or data.get("web_search_expires", 0) <= time.time()
            or not 0 <= callback_data.index < len(sounds)):
        await callback.answer(WebSearchText.EXPIRED.value, show_alert=True)
        return
    await callback.answer(WebSearchText.SENDING.value)
    sound = WebSound(**sounds[callback_data.index])
    actions = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Назад", callback_data=f"web-back:{callback_data.token}"),
        InlineKeyboardButton(text="Главное меню", callback_data="photo-home"),
    ]])
    try:
        cached_id = await web_sound_cache.get(sound.key)
        if cached_id:
            try:
                await callback.message.answer_audio(audio=cached_id, reply_markup=actions)
                return
            except TelegramBadRequest as error:
                # Recover only from invalid file IDs, not other Telegram errors.
                if not any(part in error.message.lower() for part in (
                    "file identifier", "file_id", "file reference"
                )):
                    raise
                await web_sound_cache.delete(sound.key)
        await callback.message.bot.send_chat_action(
            chat_id=callback.message.chat.id, action=ChatAction.UPLOAD_VOICE
        )
        content = await web_sound_search.download(sound)
        sent = await callback.message.answer_audio(
            audio=BufferedInputFile(content, filename="sound.mp3"),
            title=sound.title[:180], reply_markup=actions,
        )
        if sent.audio:
            await web_sound_cache.put(sound.key, sent.audio.file_id)
    except SoundSearchError as error:
        await callback.message.answer(str(error))
    except TelegramAPIError:
        logger.warning("Unable to send a web sound via Telegram")
        await callback.message.answer(WebSearchText.SEND_FAILED.value)

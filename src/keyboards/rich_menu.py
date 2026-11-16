"""Rich Message menu helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from aiogram.types import InputRichBlockButtons, InputRichBlockParagraph, InputRichMessage, ReplyKeyboardRemove, RichMessageButton, RichTextCustomEmoji, WebAppInfo

RichButtonStyle = Literal["danger", "success", "primary", "link"]


@dataclass(frozen=True, slots=True)
class RichMenuButton:
    text: str
    callback_data: str | None = None
    url: str | None = None
    web_app: WebAppInfo | None = None
    style: RichButtonStyle | None = None
    custom_emoji_id: str | None = None
    emoji_fallback: str = "•"

    def __post_init__(self) -> None:
        actions = (self.callback_data, self.url, self.web_app)
        if sum(action is not None for action in actions) != 1:
            raise ValueError("A RichMenuButton must have exactly one action.")
        if self.callback_data is not None:
            size = len(self.callback_data.encode("utf-8"))
            if not 1 <= size <= 64:
                raise ValueError("callback_data must be between 1 and 64 bytes.")
        if self.style == "link" and self.callback_data is None:
            raise ValueError("The link style is available only for callback buttons.")

    def as_telegram_button(self) -> RichMessageButton:
        button_text: str | list[str | RichTextCustomEmoji] = self.text
        if self.custom_emoji_id:
            button_text = [RichTextCustomEmoji(custom_emoji_id=self.custom_emoji_id, alternative_text=self.emoji_fallback), " ", self.text]
        return RichMessageButton(text=button_text, callback_data=self.callback_data, url=self.url, web_app=self.web_app, style=self.style)


@dataclass(frozen=True, slots=True)
class RichMenuScreen:
    text: str
    rows: Sequence[Sequence[RichMenuButton]]


def build_rich_menu(screen: RichMenuScreen) -> InputRichMessage:
    blocks: list[InputRichBlockParagraph | InputRichBlockButtons] = [InputRichBlockParagraph(text=screen.text)]
    for row in screen.rows:
        if not 1 <= len(row) <= 8:
            raise ValueError("A Rich Message button row must contain 1 to 8 buttons.")
        blocks.append(InputRichBlockButtons(buttons=[button.as_telegram_button() for button in row]))
    return InputRichMessage(blocks=blocks)


def callback_button(text: str, callback_data: str, *, style: RichButtonStyle | None = None, custom_emoji_id: str | None = None, emoji_fallback: str = "•") -> RichMenuButton:
    return RichMenuButton(text=text, callback_data=callback_data, style=style, custom_emoji_id=custom_emoji_id, emoji_fallback=emoji_fallback)


def web_app_button(text: str, web_app: WebAppInfo, *, style: RichButtonStyle | None = None, custom_emoji_id: str | None = None, emoji_fallback: str = "•") -> RichMenuButton:
    return RichMenuButton(text=text, web_app=web_app, style=style, custom_emoji_id=custom_emoji_id, emoji_fallback=emoji_fallback)


def back_button(callback_data: str) -> RichMenuButton:
    return callback_button("Назад", callback_data, style="link")


def remove_legacy_reply_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove(remove_keyboard=True)


def menu_message(
    text: str, rows: Sequence[Sequence[RichMenuButton]]
) -> InputRichMessage:
    return build_rich_menu(RichMenuScreen(text=text, rows=rows))

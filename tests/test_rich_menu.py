import unittest

from aiogram.types import WebAppInfo

from keyboards.rich_menu import RichMenuButton, RichMenuScreen, back_button, build_rich_menu


class RichMenuTest(unittest.TestCase):
    def test_preserves_label_emoji_and_action(self):
        button = RichMenuButton(
            text="Инструкция",
            callback_data="menu:help",
            custom_emoji_id="5334882760735598374",
            emoji_fallback="ℹ️",
        )
        screen = RichMenuScreen("Главное меню", [[button], [back_button("menu:home")]])
        blocks = build_rich_menu(screen).model_dump(exclude_none=True)["blocks"]
        self.assertEqual([block["type"] for block in blocks], ["paragraph", "buttons", "buttons"])
        rendered = blocks[1]["buttons"][0]
        self.assertEqual(rendered["text"][-1], "Инструкция")
        self.assertEqual(rendered["text"][0]["custom_emoji_id"], "5334882760735598374")
        self.assertEqual(rendered["callback_data"], "menu:help")
        self.assertEqual(blocks[2]["buttons"][0]["callback_data"], "menu:home")

    def test_launch_button_has_only_web_app_action(self):
        button = RichMenuButton("Угадай Звук", web_app=WebAppInfo(url="https://example.org/game"))
        rendered = button.as_telegram_button().model_dump(exclude_none=True)
        self.assertEqual(rendered["web_app"]["url"], "https://example.org/game")
        self.assertNotIn("callback_data", rendered)

    def test_rejects_invalid_callback_byte_length_and_row_size(self):
        with self.assertRaises(ValueError):
            RichMenuButton("Звук", callback_data="я" * 33)
        button = back_button("menu:home")
        with self.assertRaises(ValueError):
            build_rich_menu(RichMenuScreen("Каталог", [[button] * 9]))

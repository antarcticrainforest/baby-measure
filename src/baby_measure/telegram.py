"""Service for telegram bot communication."""
from __future__ import annotations
from base64 import b64decode
from datetime import datetime
import time

import pandas as pd
import requests
from sqlalchemy import create_engine

import telepot
from telepot.aio.delegate import pave_event_space, per_chat_id, create_open
from telepot.namedtuple import (
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from .server_utils import db_settings


class Telegram(telepot.aio.helper.ChatHandler):
    """Service that interacts with a telegram bot to query and log entries.

    Parameters
    ----------
    db_settings: settings class holding all methods to interact with the
                 settings database.
    """

    def __init__(self, bot, *args, port: int = 8051, **kwargs) -> None:

        super(Telegram, self).__init__(bot, *args, **kwargs)
        self.port = port
        self._count = 0
        self.answerer = telepot.aio.helper.Answerer(bot)

    @property
    async def me(self) -> str:
        """Get info about the bot."""
        return await self.bot.getMe()

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}/bot"

    async def get_or_add(
        self, user_id: str, last_name: str, first_name: str
    ) -> dict:
        with create_engine(db_settings.connection).connect() as conn:
            table = pd.read_sql(
                f"select * from telebot where user_id = {user_id}", conn
            )
        timestamp = pd.Timestamp(datetime.now())
        if len(table) == 0:
            # First time this user is connecting to the bot
            table = pd.DataFrame(
                {
                    "user_id": [user_id],
                    "first_name": [first_name],
                    "last_name": [last_name],
                    "login_attempts": [0],
                    "time": timestamp,
                    "allowed": [False],
                }
            )
        else:
            table["fist_name"] = first_name
            table["last_name"] = last_name
            table["time"] = timestamp
            if table["allowed"] is False:
                table["login_attempts"] += 1
        return table.iloc[0]

    async def on_chat_message(self, msg) -> None:
        img, text = await self._get_response(msg)
        if text is not None:
            await self.sender.sendMessage(text)
        if img:
            await self.sender.sendPhoto(b64decode(img.encode("utf-8")))

    async def _get_response(self, msg):

        user_id = msg["from"]["id"]
        last_name = msg["from"].get("last_name", "")
        first_name = msg["from"].get("first_name", "")
        table = await self.get_or_add(user_id, last_name, first_name)
        in_text = msg["text"]

        me = await self.me
        my_name = f"@{me['username']}"
        if msg["from"]["is_bot"]:
            return None, None
        if msg["chat"].get(
            "type", "chat"
        ) == "group" and not in_text.startswith(my_name):
            return None, None
        in_text = in_text.split(my_name)[-1]
        attempts = table["login_attempts"]
        secret = db_settings.db_settings["tg_secret"]
        img, text = None, "Got it!"
        if bool(table["allowed"]) is True:
            try:
                res = requests.get(self.url, params={"text": in_text}).json()
                text = res.get("text", "Internal Error :(")
                img = res.get("img", "")
                return img, text
            except requests.exceptions.ConnectionError:
                return None, "Server not running :("
        if attempts >= 3:
            return None, "Got it!"
        if attempts == 0:
            if in_text != secret:
                text = (
                    "To get and set information you must enter the secret "
                    "phrase, the phrase was set by who ever installed me. "
                    "Enter the phrase now:\n"
                )
            else:
                text = "Great! You can now send me commands or ask questions."
                table["allowed"] = int(True)
        elif attempts > 0 and bool(table["allowed"]) is False:
            if in_text != secret:
                text = (
                    "This was the wrong secret phrase, please try again - "
                    f" you have {3 - attempts} attempts left:\n"
                )
            else:
                text = "Great! You can now send me commands or ask questions."
                table["allowed"] = int(True)
        if not bool(table["allowed"]) is False:
            table["login_attempts"] += 1
        await self._update_user(user_id, table)
        return img, text

    async def _update_user(self, uid, table):
        keys = (
            "user_id",
            "first_name",
            "last_name",
            "login_attempts",
            "allowed",
        )
        alter_items = []
        add_items = []
        for k in keys:
            if isinstance(table[k], str):
                alter_items.append(f"{k} = '{table[k]}'")
                add_items.append(f"'{table[k]}'")
            else:
                alter_items.append(f"{k} = {table[k]}")
                add_items.append(f"{table[k]}")
        update = ", ".join(alter_items)
        with create_engine(db_settings.connection).connect() as conn:
            exists = conn.execute(
                f"select * from telebot where user_id = {uid}"
            )
            if len(exists.fetchall()) > 0:
                conn.execute(
                    f"update telebot set {update} where user_id = {uid}"
                )
            else:
                conn.execute(
                    f"insert into telebot ({', '.join(keys)}) "
                    f"values ({', '.join(add_items)});"
                )

    async def on_callback_query(self, msg):
        query_id, from_id, query_data = telepot.glance(
            msg, flavor="callback_query"
        )
        print("Callback Query:", query_id, from_id, query_data)

        text = await self._get_response(msg)
        if text is not None:
            self.bot.answerCallbackQuery(query_id, text=text)

    @staticmethod
    def bot_from_token(token: str, port: int = 8050):
        return telepot.aio.DelegatorBot(
            token,
            [
                pave_event_space()(
                    per_chat_id(), create_open, Telegram, port=port, timeout=10
                ),
            ],
        )

    async def on_inline_query(self, msg):
        print(msg)

        def compute():
            query_id, from_id, query_string = telepot.glance(
                msg, flavor="inline_query"
            )
            print("Inline Query:", query_id, from_id, query_string)

            articles = [
                InlineQueryResultArticle(
                    id="abc",
                    title=query_string,
                    input_message_content=InputTextMessageContent(
                        message_text=query_string
                    ),
                )
            ]

            return articles

        await self.answerer.answer(msg, compute)

    async def on_chosen_inline_result(self, msg):
        print(msg)
        result_id, from_id, query_string = telepot.glance(
            msg, flavor="chosen_inline_result"
        )
        print("Chosen Inline Result:", result_id, from_id, query_string)

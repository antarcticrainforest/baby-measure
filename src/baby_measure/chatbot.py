"""Interface for a chatbot."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import string
from tempfile import TemporaryDirectory
from typing import NamedTuple, Union

from flask import request
from flask_restful import reqparse, abort, Resource
import numpy as np

import pandas as pd
from .utils import DBSettings, background
from .server_utils import db_settings, gh_page, plot


Instructions = NamedTuple(
    "Instructions",
    [
        ("instruction", str),
        ("content", str),
        ("amount", Union[float, None]),
        ("when", Union[datetime, str]),
        ("table", str),
    ],
)


class ChatBot(Resource):
    """A simple chatbot."""

    gh_page = gh_page
    plot = plot
    db_settings = db_settings
    greetings: list[str] = [
        "hi",
        "hi there",
        "hola",
        "hallo",
        "hello",
        "guten tag",
        "what's up",
        "whassup",
        "hey",
        "hei",
        "hej",
    ]
    action_instruction: dict[str, str] = {
        "set": "log",
        "setze": "log",
        "put": "log",
        "log": "log",
        "logg": "log",
        "adjust": "edit",
        "edit": "edit",
        "del": "del",
        "delete": "del",
        "remove": "del",
        "get": "get",
        "when": "get",
        "what": "get",
        "how": "get",
        "tell": "get",
    }
    table_types: dict[str, str] = {
        "nappy": "nappie",
        "nappie": "nappie",
        "daiper": "nappie",
        "formula": "mamadera",
        "milk": "mamadera",
        "nursing": "leche",
        "breastmilk": "mamadera",
        "poop": "nappie",
        "poo": "nappie",
        "pee": "nappie",
        "head": "body",
        "size": "body",
        "lenght": "body",
        "height": "body",
        "long": "body",
        "weight": "body",
        "heavy": "body",
        "light": "body",
        "tall": "body",
        "small": "body",
    }

    def _split_text(self, text: str) -> list[str]:

        text_words = [t for t in text.split() if t.strip()]
        punctuations = string.punctuation.strip("-").strip(":")
        out_words = []
        for word in text_words:
            for punctuation in punctuations:
                word = word.strip(punctuation)
            if word not in self.greetings:
                out_words.append(word)
        return out_words

    def _extract_instruction(self, words: list[str]) -> Instructions:
        instruction, table = "", ""
        content: str = ""
        amount: float | None = None
        dates: datetime | str | None = None
        for word in words:

            if word in self.action_instruction and not instruction:
                instruction = self.action_instruction[word]
            elif word in self.table_types and not table:
                table = self.table_types[word]
                content = word
            try:
                amount = float(word)
            except ValueError:
                pass
            if dates is None:
                try:
                    dates = pd.Timestamp(word).to_pydatetime()
                except ValueError:
                    pass
        if table == "nappie":
            if "poo" in words or "poop" in words:
                content = "poop"
            elif "pee" in words:
                content = "pee"
            else:
                content = ""
            amount = None
        if "last" in words:
            dates = "last"
        if "long" in words or "dur" in words or "duration" in words:
            table = "breastfeeding"

        return Instructions(
            instruction=instruction,
            table=table,
            when=dates or "last",
            amount=amount,
            content=content,
        )

    @background
    def _save_and_commit(self):

        total_amount_fig = self.plot.amount
        daily_amount_fig = self.plot.daily_amount
        breastfeeding_fig = self.plot.breastfeeding
        weight_fig = self.plot.plot_body("weight", "Weight [km]", "Body Weight")
        height_fig = self.plot.plot_body("height", "Height [cm]", "Body Height")
        head_fig = self.plot.plot_body("head", "Size [cm]", "Head Size")
        nappy_fig = self.plot.nappy
        self.plot.save_plots(
            total_amount_fig,
            daily_amount_fig,
            breastfeeding_fig,
            weight_fig,
            height_fig,
            height_fig,
            nappy_fig,
        )
        if self.gh_page.use_gh_pages and self.gh_page._item_queue.empty():
            with self.gh_page._lock:
                self.gh_page._item_queue.put("block")
                with TemporaryDirectory() as repo_dir:
                    self.gh_page._commit(Path(repo_dir))
                _ = self.gh_page._item_queue.get()

    def _log_db(
        self,
        content: str,
        when: datetime | str,
        table: str,
        amount: float | None,
    ) -> str:
        if not table:
            return "I could not retrieve the information from the database"
        idx = self.db_settings.db_index
        if isinstance(when, datetime):
            time = when
        else:
            time = datetime.now()
        if table in ["mamadera", "body", "breastfeeding"] and amount is None:
            return "You must give a numeric value to log."
        if table == "mamadera" and content == "formula":
            df = pd.DataFrame(
                {
                    "id": [idx],
                    "time": [time],
                    "amount": [float(amount)],
                    "type": ["formula"],
                }
            )
        elif table == "mamadera":
            df = pd.DataFrame(
                {
                    "id": [idx],
                    "time": [time],
                    "amount": [float(amount)],
                    "type": ["breastmilk"],
                }
            )
        elif table == "breastfeeding":
            df = pd.DataFrame(
                {"id": [idx], "time": [time], "duration": [float(amount)]}
            )
        elif table == "body":
            values = {
                "id": [idx],
                "time": [time],
                "height": [None],
                "weight": [None],
                "head": [None],
            }
            if content in ("height", "length"):
                values["height"] = float(amount)
            elif content in ("weight",):
                values["weight"] = float(amount)
            elif content in ("head", "size"):
                values["head"] = float(amount)
            else:
                return (
                    "Could not determine measurment type, use one of the "
                    "following keywords: 'height', 'lenght', 'weight', "
                    "'head', 'size'"
                )
            df = pd.DataFrame(values)
        else:
            if content.startswith("poo"):
                ctype = "poop"
            else:
                ctype = "pee"
            df = pd.DataFrame({"id": [idx], "time": [time], "type": [ctype]})

        # self.append_db(table_name, df)
        self._save_and_commit()
        columns = [c for c in df.columns if c != "id"]
        df["time"] = df["time"].dt.strftime("%a %_d. %b %R")
        out = (
            f"The following content has been added to the {table} db:\n"
            f"{df[columns].to_string(index=False)}"
        )
        if self.gh_page.gh_page_url:
            out += (
                "\nNew plots have been created and should be available shortly "
                f"under:\n {self.gh_page.gh_page_url}"
            )
        return out

    def _read_db(self, content: str, when: datetime | str, table: str) -> str:
        if not table:
            return "I could not retrieve the information from the database"
        key = "type"
        entries = self.db_settings.read_db(table)
        if table == "mamadera" and content != "formula":
            content = "breastmilk"
        elif table == "breastfeeding":
            content = ""
        if content and table != "body":
            for column in entries.columns:
                subset = entries.loc[entries[column] == content]
                if len(subset):
                    entries = subset
        if isinstance(when, datetime):
            diff = pd.DatetimeIndex(entries["time"]) - when
            idx = np.argmin(np.fabs(diff.total_seconds()))
            last = entries.iloc[idx]
        else:
            last = entries.iloc[-1]
        day = pd.DatetimeIndex([last["time"].date()])
        time = last["time"].strftime("%a %_d. %b %R")
        if table == "body":
            return f"Measures from {time}:\n{last[['weight', 'height', 'head']].to_string()}"
        daily = entries.groupby(pd.Grouper(freq="1D")).sum(numeric_only=True).loc[day]
        amount_key = [c for c in last.keys() if c not in ("id", "uid", "time")][0]
        try:
            amount = float(last[amount_key])
            daily_amount = float(daily[amount_key])
            if daily_amount == amount:
                daily_values = ""
            else:
                daily_values = f" (sum that day: {daily_amount})"
            return f"The {content} amount from {time} was {amount} {daily_values}"
        except ValueError:
            amount = last[amount_key]
            daily_values = int(daily["count"])
        return (
            f"On {time} the nappy content was {amount} (total: {daily_values} nappies)"
        )

    def _process_text(self, text: str):
        """Extract the instructions from a text."""
        word_list = self._split_text(text.lower())
        instruction = self._extract_instruction(word_list)
        inst = instruction.instruction
        print(instruction)
        if not inst:
            inst = "get"
        if not instruction.table:
            return "Sorry, I didn't get that"
        if inst == "get":
            return self._read_db(
                instruction.content, instruction.when, instruction.table
            )
        elif inst == "log":
            return self._log_db(
                instruction.content,
                instruction.when,
                instruction.table,
                instruction.amount,
            )
        return "Sorry, I didn't get that"

    def _abort(self):
        abort(405, message="The method is not allowed for the requested URL.")

    def get(self):
        self._abort()

    def put(self):
        self._abort()

    def delete(self):
        self._abort()

    def post(self, *args):
        """Get the information from the text."""
        text = request.args.get("text")
        if not text:
            self._abort("Key should have text")
        text = self._process_text(text)
        return {"message": text}, 200


if __name__ == "__main__":

    from flask_restful import Api
    from flask import Flask

    sever = Flask(__name__)
    chatbot = Api(sever)
    chatbot.add_resource(ChatBot, "/bot")
    sever.run(debug=True, host="0.0.0.0", port=str(8050))

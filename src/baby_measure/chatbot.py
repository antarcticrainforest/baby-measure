"""Interface for a chatbot."""
from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
import re
import string
import subprocess
from tempfile import TemporaryDirectory
from typing import NamedTuple, Union

from flask import request
from flask_restful import reqparse, abort, Resource
import pandas as pd
import numpy as np

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
        "nursing": "breastfeeding",
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
        "bottle": "mamadera",
    }

    def _split_text(self, text: str) -> tuple[list[str], datetime | None]:

        date, text = self._extract_datetime(text)
        text_words = [t for t in text.split() if t.strip()]
        punctuations = string.punctuation.strip("-").strip(":")
        out_words = []
        for word in text_words:
            for punctuation in punctuations:
                word = word.strip(punctuation)
            if word not in self.greetings:
                out_words.append(word)
        return out_words, date

    def _check_for_weekdays(self, txt: str) -> tuple[str, str]:

        weekdays = {
            "monday": "mon",
            "tuesday": "tue",
            "wednesday": "wed",
            "thursday": "thur",
            "friday": "fri",
            "saturday": "sat",
            "sunday": "sun",
        }
        words = txt.split()
        for long_w, short_w in weekdays.items():
            if short_w not in txt and long_w not in txt:
                continue
            if short_w in words:
                break_word = short_w
                txt = txt.replace(short_w, "")
            else:
                break_word = weekdays[long_w]
                txt = txt.replace(long_w, "")
            ndays = 1
            while True:
                last_day = datetime.now() - timedelta(hours=ndays * 24)
                if last_day.strftime("%a").lower() == break_word:
                    return last_day.strftime("%Y-%m-%d"), txt
                ndays += 1
        return "", txt

    def _extract_datetime(self, txt: str) -> tuple[datetime | None, str]:
        """Use a regex pattern to extract a datetime."""
        date_regex = (
            r"(\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{1,4}[./-]\d{1,2}[./-]\d{2})"
        )
        month_regex = r"(\d{1,2}[./-]\d{2})"
        time_regex = r"([01]?[0-9]|2[0-3]):[0-5][0-9]"
        date_search = re.search(date_regex, txt)
        time_search = re.search(time_regex, txt)
        month_search = re.search(month_regex, txt)
        date_string, txt = self._check_for_weekdays(txt)
        if "the day before yesterday" in txt:
            old = datetime.now() - timedelta(days=2)
            date_string = f"{old.year}-{old.month}-{old.day}"
            txt = txt.replace("the day before yesterday")
        elif "yesterday" in txt:
            old = datetime.now() - timedelta(days=1)
            date_string = f"{old.year}-{old.month}-{old.day}"
            txt = txt.replace("yesterday")
        elif date_search:
            date_string = date_search.group()
            txt = txt.replace(date_string, "")
        elif not date_string:
            if month_search:
                month_string = (
                    month_search.group().replace(".", "-").replace("/", "-")
                )
                date_string = f"{datetime.now().strftime('%Y')}-{month_string}"
            else:
                date_string = ""
        if time_search:
            time_string = time_search.group()
            if not date_string:
                date_string = datetime.now().strftime("%Y-%m-%d")
            txt = txt.replace(time_string, "")
            date_string += f"T{time_string}"
        date = None
        if date_string:
            try:
                date = pd.Timestamp(date_string).to_pydatetime()
            except (ValueError, TypeError):
                pass
        return date, txt

    def _extract_instruction(
        self, words: list[str], dates: datetime | None
    ) -> Instructions:
        instruction, table = "", ""
        content: str = ""
        amount: float | None = None
        mamadera_markers = [
            k for (k, v) in self.table_types.items() if v == "mamadera"
        ]
        for word in words:

            if word in self.action_instruction and not instruction:
                instruction = self.action_instruction[word]
            elif word in mamadera_markers and not table:
                table = "mamadera"
                content = word
            elif word in self.table_types and not table:
                table = self.table_types[word]
                content = word
            if amount is None:
                try:
                    amount = float(word)
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
        if "last" in words and dates is None:
            dates = "last"
        if (
            "long" in words
            or "dur" in words
            or "duration" in words
            or "feeding" in words
            or "breastfeeding" in words
        ):
            if table != "mamadera":
                table = "breastfeeding"
        if "feeding" in words and "milk" in words:
            table = "mamadera"
            content = "breastmilk"

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
        weight_fig = self.plot.plot_body(
            "weight", "Weight [km]", "Body Weight"
        )
        height_fig = self.plot.plot_body(
            "height", "Height [cm]", "Body Height"
        )
        head_fig = self.plot.plot_body("head", "Size [cm]", "Head Size")
        nappy_fig = self.plot.nappy
        self.plot.save_plots(
            total_amount_fig,
            daily_amount_fig,
            breastfeeding_fig,
            weight_fig,
            height_fig,
            head_fig,
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

        self.db_settings.append_db(table, df)
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

    @staticmethod
    def _get_body_measure(table: pd.DataFrame) -> str:
        time = table["time"].strftime("%a %_d. %b %R")
        return f"Measures from {time}:\n{table[['weight', 'height', 'head']].to_string()}"

    @staticmethod
    def _get_nappy_text(last: pd.DataFrame, table: pd.DataFrame) -> str:

        time = last["time"].strftime("%a %_d. %b %R")
        day = pd.DatetimeIndex([last["time"].date()])
        count = int(
            table.groupby(pd.Grouper(freq="1D")).count().loc[day]["type"]
        )
        content = str(last["type"])
        return (
            f"On {time} the nappy content was {content} "
            f"(with a total of {count} nappies that day)"
        )

    @staticmethod
    def _get_feeding_text(
        last: pd.DataFrame, table: pd.DataFrame, content: str | None
    ) -> str:

        time = last["time"].strftime("%a %_d. %b %R")
        day = pd.DatetimeIndex([last["time"].date()])
        content = content or ""
        if content:
            daily_sum = float(
                table.loc[table["type"] == content]["amount"]
                .groupby(pd.Grouper(freq="1D"))
                .sum()
                .loc[day]
            )
            this_time = float(last["amount"])
            content = f"{content} "
            amount = "amount"
        else:
            daily_sum = float(
                table["duration"].groupby(pd.Grouper(freq="1D")).sum().loc[day]
            )
            this_time = float(last["duration"])
            amount = "duration"
        daily_values = f"(total that day: {daily_sum})"
        return (
            f"The {content}{amount} from {time} was {this_time} {daily_values}"
        )

    def _read_db(self, content: str, when: datetime | str, table: str) -> str:
        if not table:
            return "I could not retrieve the information from the database"
        entries = self.db_settings.read_db(table)
        entries = entries.set_index(pd.DatetimeIndex(entries["time"].values))
        if table == "mamadera" and content != "formula":
            content = "breastmilk"
        elif table == "breastfeeding":
            content = ""
        if content.strip() and table != "body":
            subset = entries.loc[entries["type"] == content]
            if not len(subset):
                subset = entries
        else:
            subset = entries
        if isinstance(when, datetime):
            diff = (pd.DatetimeIndex(subset["time"]) - when).total_seconds()
            idx = np.where(diff > 0, diff, np.inf).argmin()
        else:
            idx = -1
        subset = subset.iloc[idx]
        if table == "body":
            text = self._get_body_measure(subset)
        elif table == "nappie":
            text = self._get_nappy_text(subset, entries)
        else:
            text = self._get_feeding_text(subset, entries, content)
        return text

    @property
    def _uptime(self) -> str:
        try:
            res = subprocess.run(
                ["uptime"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            return "I can't get you this information."
        return res.stdout.decode()

    def _process_text(self, text: str):
        """Extract the instructions from a text."""
        word_list, date = self._split_text(text.lower())
        if "uptime" in word_list or "online" in word_list:
            return self._uptime
        instruction = self._extract_instruction(word_list, date)
        inst = instruction.instruction
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

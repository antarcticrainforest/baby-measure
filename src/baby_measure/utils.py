"""Collection of utilities to run and setup the geojson viewer app."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
from getpass import getpass
import logging
from pathlib import Path
import json
import os
import time
from typing import Any, Callable, Iterator

import appdirs
from dash import html, dcc
from dash_datetimepicker import DashDatetimepickerSingle
import pandas as pd
from sqlalchemy import create_engine, text

logging.basicConfig(format="%(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger("baby-measure")


def _utc_timestep_to_local_timestep(utc: datetime) -> datetime:

    epoch = time.mktime(utc.timetuple())
    offset = datetime.fromtimestamp(epoch) - datetime.utcfromtimestamp(epoch)
    return utc + offset


@contextmanager
def set_env_var(key: str, value: str) -> Iterator[None]:
    old_value = os.environ.get(key)
    try:
        os.environ[key] = value
        yield
    finally:
        del os.environ[key]
        if old_value:
            os.environ[key] = old_value


def str_to_timestamp(inp_time: str) -> datetime:
    """Convert a iso timestamp to a datetime."""

    timestamp = datetime.fromisoformat(inp_time.strip("Z"))
    if "Z" in inp_time:
        timestamp = _utc_timestep_to_local_timestep(
            timestamp.replace(tzinfo=timezone.utc)
        )
    return timestamp.replace(tzinfo=None)


def set_date_picker(id: str) -> list[DashDatetimepickerSingle, html.Button]:
    """Set a new date picker."""
    return html.Div(
        id=f"{id}-timepicker",
        children=[
            DashDatetimepickerSingle(
                id=f"{id}-timepicker-obj",
                date=datetime.now().strftime("%Y-%m-%dT%H:%M"),
                locale="en-il",
                utc=False,
            )
        ],
    )


def get_entry(
    header: str,
    id: str,
    dcc_input: list[dcc.Inpt | dcc.Dropdown],
    label: str | None = None,
) -> html.Div:
    """Create the entries for a measurement input field."""
    children = [html.H4(f"Log {header}:")]
    if label:
        children += [html.Label(label or "", id=f"{id}-label"), html.Br()]

    children += [
        html.Div(
            id=f"{id}-time",
            children=[
                set_date_picker(id),
                html.Button(
                    id=f"{id}-now-button",
                    n_clicks=0,
                    children="Now",
                    className="now",
                ),
            ],
            style={"display": "inline-grid"},
        ),
        html.Br(),
    ]
    for nn, inp in enumerate(dcc_input):
        children.append(inp)
        if nn <= len(dcc_input) - 1:
            children.append(html.Br())
    return html.Div(
        id=id,
        children=children,
        style={
            "textAlign": "center",
            "justify-content": "center",
        },
    )


class DBSettings:
    """Class holding information for the database."""

    db_settings: dict[str, str] = {}
    _tables: dict[str, pd.DataFrame] = {}

    def __init__(self):
        self.configure()
        self._last_connection = {}

    def _set_db(self, table: str) -> None:
        with create_engine(self.connection, pool_recycle=3600).connect() as conn:
            entries = pd.read_sql(text(f"select * from {table}"), conn)
        self._tables[table] = entries.sort_values("time")
        self._last_connection[table] = datetime.now()

    def alter_table(self, statement: str, table: str) -> None:
        with create_engine(self.connection, pool_recycle=3600).begin() as conn:
            conn.execute(text(statement))
        self._set_db(table)

    def read_db(self, table: str, override: bool = False) -> pd.DataFrame:
        """Read the content of a db_table."""
        if self._tables.get(table) is None or override:
            self._set_db(table)
        now = datetime.now()
        if (now - self._last_connection.get(table, now)).total_seconds() > 300:
            self._set_db(table)
        return self._tables[table]

    def append_db(self, table: str, data_frame: pd.DataFrame) -> None:
        with create_engine(self.connection, pool_recycle=3600).begin() as conn:
            data_frame.to_sql(
                table,
                conn,
                index=False,
                if_exists="append",
            )
        self._tables[table] = None

    def add_entry_tab(self) -> list:
        return [
            get_entry(
                "Formula",
                "mamadera",
                [
                    dcc.Input(
                        type="number",
                        placeholder="Amount [ml]",
                        id="mamadera-amount",
                    )
                ],
                label=self.last_entry(
                    "mamadera",
                    "amount",
                    ("type", "formula"),
                ),
            ),
            get_entry(
                "Breast Milk",
                "saca_leche",
                [
                    dcc.Input(
                        type="number",
                        placeholder="Amount [ml]",
                        id="leche-amount",
                    )
                ],
                label=self.last_entry(
                    "mamadera",
                    "amount",
                    ("type", "breastmilk"),
                ),
            ),
            get_entry(
                "Breast Feeding",
                "leche",
                [
                    dcc.Input(
                        type="number",
                        placeholder="Duration [min]",
                        id="leche-dur",
                    )
                ],
                label=self.last_entry(
                    "breastfeeding",
                    "duration",
                ),
            ),
            get_entry(
                "Body Measure",
                "body",
                [
                    dcc.Input(type="number", placeholder="Weight [kg]", id="weight"),
                    dcc.Input(type="number", placeholder="Length [cm]", id="length"),
                    dcc.Input(type="number", placeholder="Head size [cm]", id="head"),
                ],
                label=self.last_entry(
                    "body",
                    None,
                ),
            ),
            get_entry(
                "Nappy content",
                "nappy",
                [
                    dcc.Dropdown(
                        ["Pee", "Poop"],
                        placeholder="Content type",
                        id="nappy-content",
                        style={
                            "width": "100%",
                            "min-width": "190px",
                            "display": "flex",
                            "justify-content": "center",
                            "textAlign": "left",
                        },
                    )
                ],
                label=self.last_entry(
                    "nappie",
                    "type",
                ),
            ),
            html.Div(
                [
                    html.Button(
                        id="submit-button",
                        n_clicks=0,
                        children="Log all entries",
                        className="log",
                    ),
                ],
                style={"display": "flex", "justify-content": "center"},
            ),
        ]

    @property
    def db_index(self):
        """Create a db index from a timestamp."""
        return int(round(datetime.utcnow().timestamp() * 10, 0))

    @property
    def connection(self) -> str:
        """Create the database connection."""
        return "mysql+pymysql://{user}:{passwd}@{host}/{db}".format(
            user=self.db_settings["db_user"],
            passwd=self.db_settings["db_passwd"],
            host=self.db_settings["db_host"],
            db=self.db_settings["db_name"],
        )

    def last_entry(
        self,
        table: str,
        key: str | None,
        extra_key: tuple[str, str] | None = None,
    ) -> str:
        entries = self.read_db(table)
        print(entries)
        if extra_key:
            entries = entries.loc[entries[extra_key[0]] == extra_key[1]]
        entry = "No entries yet"
        if len(entries):
            last = entries.iloc[-1]
            time = last["time"].strftime("%a %R")
            if key:
                entry = f"Last: {last[key]} at {time}"
            else:
                entry = f"Last: at {time}"
        return entry

    def log_entries(
        self, entries: dict[str, int | None], times: dict[str, datetime]
    ) -> int:
        """Log all relevant entries to the database."""
        idx = self.db_index
        amount = pd.DataFrame(columns=["id", "time", "amount", "type"])
        body = pd.DataFrame(columns=["id", "time", "height", "weight", "head"])
        nappy = pd.DataFrame(columns=["id", "time", "type"])
        breastfeeding = pd.DataFrame(columns=["id", "time", "duration"])
        if entries["mamadera_amount"]:
            amount = pd.concat(
                [
                    amount,
                    pd.DataFrame(
                        {
                            "id": [idx],
                            "time": [times["mamadera_formula"]],
                            "amount": [entries["mamadera_amount"]],
                            "type": ["formula"],
                        },
                        index=[idx],
                    ),
                ]
            )
        if entries["leche_amount"]:
            amount = pd.concat(
                [
                    amount,
                    pd.DataFrame(
                        {
                            "id": [idx + 1],
                            "time": [times["mamadera_leche"]],
                            "amount": [entries["leche_amount"]],
                            "type": ["breastmilk"],
                        },
                        index=[idx + 1],
                    ),
                ]
            )
        if entries["leche_duration"]:
            breastfeeding = pd.DataFrame(
                {
                    "id": [idx],
                    "time": [times["leche"]],
                    "duration": [entries["leche_duration"]],
                },
                index=[idx],
            )
        if entries["nappy_content"]:
            nappy = pd.DataFrame(
                {
                    "id": [idx],
                    "time": [times["nappy"]],
                    "type": [entries["nappy_content"].lower()],
                },
                index=[idx],
            )
        if entries["weight"] or entries["head"] or entries["length"]:
            body = pd.DataFrame(
                {
                    "id": [idx],
                    "time": [times["body"]],
                    "height": [entries["length"]],
                    "weight": [entries["weight"]],
                    "head": [entries["head"]],
                },
                index=[idx],
            )
        tables = dict(
            mamadera=amount,
            body=body,
            breastfeeding=breastfeeding,
            nappie=nappy,
        )
        num_logs = 0
        for table_name, data_frame in tables.items():
            if len(data_frame) > 0:
                num_logs += 1
                self.append_db(table_name, data_frame)
        return num_logs

    @staticmethod
    def gather_config(
        inp_file: Path, defaults: dict[str, str], manual_config: bool = False
    ) -> dict[str, str]:
        """Create a new config file."""
        db_settings = dict(
            db_host=os.environ.get("MYSQL_ROOT_HOST")
            or input(f"DB server [{defaults['db_host']}]: ").strip()
            or defaults["db_host"],
            db_port=os.environ.get("MYSQL_PORT")
            or input(f"DB port [{defaults['db_port']}]: ").strip()
            or defaults["db_port"],
            db_name=os.environ.get("MYSQL_DATABASE")
            or input(f"DB name [{defaults['db_name']}]: ").strip()
            or defaults["db_name"],
            db_user=os.environ.get("MYSQL_USER")
            or input(f"DB user name [{defaults['db_user']}]: ").strip()
            or defaults["db_user"],
            db_passwd=os.environ.get("MYSQL_PASSWORD") or getpass("DB passwd: "),
            tg_token=None,
        )
        inp_file.parent.mkdir(exist_ok=True, parents=True)
        if manual_config is True:
            init_telegram = (
                input(
                    "Use a telegram chatbot service to log and query entries? [y|N] "
                ).strip()
                or "n"
            )
            if init_telegram.lower().startswith("y"):
                db_settings["tg_token"] = input(
                    f"Enter API token [{defaults.get('tg_token', '')}]: "
                ).strip() or defaults.get("tg_token", "")
                db_settings["tg_secret"] = input(
                    "Set a secret sentence you give to users to authorisation:\n"
                ).strip() or defaults.get("tg_secret", "")
                if not db_settings["tg_secret"]:
                    raise ValueError("You must give a secret sentence.")
        with inp_file.open("w", encoding="utf-8") as f_obj:
            json.dump(db_settings, f_obj, indent=3)
        inp_file.chmod(0o600)
        return db_settings

    @classmethod
    def create_tables(
        cls,
        db_host: str,
        db_port: str,
        db_name: str,
        db_user: str,
        db_passwd: str,
    ) -> None:
        conn = "mysql+pymysql://{user}:{passwd}@{host}/{db}".format(
            user=db_user,
            passwd=db_passwd,
            host=db_host,
            db=db_name,
        )

        tables = (
            (
                "CREATE TABLE IF NOT EXISTS `body` ( `id` BIGINT(20) UNSIGNED NOT NULL, "
                "`time` TIMESTAMP NOT NULL, `height` FLOAT(10,3), `weight` "
                "FLOAT(10,3), `head` FLOAT(10,3), PRIMARY KEY (`id`) );"
            ),
            (
                "CREATE TABLE IF NOT EXISTS `nappie` ( `id` BIGINT(20) "
                "UNSIGNED NOT NULL, `time` TIMESTAMP NOT NULL, `type` "
                'ENUM("pee", "poop") NOT NULL, PRIMARY KEY (`id`) );'
            ),
            (
                "CREATE TABLE IF NOT EXISTS `breastfeeding` ( `id` BIGINT(20) "
                "UNSIGNED NOT NULL, `time` TIMESTAMP NOT NULL, `duration` "
                "BIGINT(20) UNSIGNED NOT NULL, PRIMARY KEY (`id`) );"
            ),
            (
                "CREATE TABLE IF NOT EXISTS `mamadera` ( `id` BIGINT(20) "
                "UNSIGNED NOT NULL, `time` TIMESTAMP NOT NULL, `amount` "
                "BIGINT(20) UNSIGNED NOT NULL, `type` "
                'ENUM("breastmilk", "formula") NOT NULL, PRIMARY KEY (`id`) );'
            ),
            (
                "CREATE TABLE IF NOT EXISTS `telebot` (`id` BIGINT(20) "
                "UNSIGNED NOT NULL AUTO_INCREMENT, "
                "`user_id` BIGINT(20) NOT NULL, "
                "`first_name` varchar(255), "
                "`last_name` varchar(255), "
                "`login_attempts` int, "
                "`time` TIMESTAMP, "
                "`allowed` BOOLEAN not null default 0, "
                "PRIMARY KEY (`id`) );"
            ),
        )
        with create_engine(conn, pool_recycle=3600).begin() as db_conn:
            for statement in tables:
                db_conn.execute(text(statement))

    @classmethod
    def configure(cls, reconfigure: bool = False) -> None:
        """Write/Read the database config."""
        defaults = {
            "db_host": "localhost",
            "db_port": "3306",
            "db_name": "baby_measure",
            "db_user": "baby",
        }
        db_settings_file = (
            Path(appdirs.user_config_dir()) / "baby-measure" / "db_config.json"
        )
        db_settings_file = Path(
            os.environ.get("BABY_CONFIG_FILE", db_settings_file) or db_settings_file
        )
        try:
            with db_settings_file.open() as f_obj:
                settings = json.load(f_obj)
        except FileNotFoundError:
            settings = cls.gather_config(db_settings_file, defaults)
        if reconfigure:
            defaults.update(settings)
            settings = cls.gather_config(db_settings_file, defaults, manual_config=True)
        cls.db_settings = settings
        cls.create_tables(
            settings["db_host"],
            settings["db_port"],
            settings["db_name"],
            settings["db_user"],
            settings["db_passwd"],
        )
        return cls.db_settings

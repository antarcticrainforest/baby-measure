"""Module for editing db entries."""

from __future__ import annotations
from datetime import datetime

from dash import html, dcc
import pandas as pd

from .utils import DBSettings

style = {
    "width": "100%",
    "min-width": "210px",
    "display": "flex",
    "justify-content": "center",
    "textAlign": "left",
}


class Edit:
    """Edit the database entries."""

    def __init__(self, db_settings: DBSettings):

        self.db_settings = db_settings

    def read_db(self, table: str) -> pd.DataFrame:
        """Read the content of a db_table."""
        return self.db_settings.read_db(table)

    def alter_table(
        self,
        table: str,
        index: int | None,
        values: dict[str, int | float | None],
        action: str,
        allow_empty: bool = False,
    ) -> None:
        """Change the content of a database."""
        if index is None:
            return
        if action == "del":
            statement = f"delete from {table} where id = {index};"
        else:
            time = self.read_db(table)[["id", "time"]]
            values["time"] = (
                time.loc[time.id == index]["time"].iloc[0].strftime("%Y-%m-%d %H:%M")
            )
            alter_items = []
            for k, v in values.items():
                if v is None and not allow_empty:
                    continue
                elif v is None:
                    alter_items.append(f"{k} = null")
                elif isinstance(v, str):
                    alter_items.append(f"{k} = '{v}'")
                else:
                    alter_items.append(f"{k} = {v}")
            if not alter_items:
                return
            alter = ", ".join(alter_items)
            statement = f"update {table} set {alter} where id = {index};"
        self.db_settings.alter_table(statement, table)

    def create_dropdown(self, key: str, title: str, data: pd.DataFrame) -> html.div:

        dtype = [
            type(data[d].iloc[0]) for d in data.columns if d not in ("time", "id")
        ][0]
        inp_obj = dcc.Input(
            id=f"{key}-field",
            type="number",
            style={"min-width": "210px"},
            placeholder="Edit entry",
        )

        if dtype == str:
            inp_obj = dcc.Dropdown(
                [
                    {"label": "Pee", "value": "pee"},
                    {"label": "Poo", "value": "poop"},
                ],
                id=f"{key}-field",
                placeholder="Edit entry",
                style=style,
            )
        children = [
            html.H4(f"Edit {title}:"),
            dcc.Dropdown(
                id=f"{key}-index-select",
                style=style,
                options=[
                    {
                        "label": data.time.iloc[i - 1].strftime("%a %d. %b %Y %H:%M"),
                        "value": data.id.iloc[i - 1],
                    }
                    for i in range(len(data), 0, -1)
                ],
            ),
            inp_obj,
        ]
        return html.Div(
            id=key,
            children=children,
            style={
                "textAlign": "center",
                "justify-content": "center",
                "min-width": "210px",
            },
        )

    @property
    def children(self) -> list[html.Div]:
        mamadera = self.read_db("mamadera")
        nappy = self.read_db("nappie")
        body = self.read_db("body")
        feeding = self.read_db("breastfeeding")
        return [
            self.create_dropdown(
                "edit-formula",
                "Formula amount",
                mamadera.loc[mamadera.type == "formula"],
            ),
            self.create_dropdown(
                "edit-milk",
                "Breast milk amount",
                mamadera.loc[mamadera.type == "breastmilk"],
            ),
            self.create_dropdown("edit-feeding", "Feeding duration", feeding),
            self.create_dropdown(
                "edit-weight", "Edit weight", body[["id", "time", "weight"]]
            ),
            self.create_dropdown(
                "edit-height", "Edit height", body[["id", "time", "height"]]
            ),
            self.create_dropdown(
                "edit-head", "Edit head size", body[["id", "time", "head"]]
            ),
            self.create_dropdown("edit-nappy", "Edit nappy content", nappy),
            html.Div(html.Br()),
            html.Div(
                id="edit-all-entries",
                children=[
                    html.Div(
                        [
                            html.Br(),
                            dcc.RadioItems(
                                [
                                    {"label": "Edit or ", "value": "edit"},
                                    {
                                        "label": "Delete Entries",
                                        "value": "del",
                                    },
                                ],
                                value="edit",
                                id=f"edit-action",
                                style=style,
                            ),
                            html.Br(),
                            html.Button(
                                id="edit-entries",
                                n_clicks=0,
                                children="Change all entries",
                                className="log",
                                style={"min-width": "210px"},
                            ),
                        ],
                        style={
                            "textAlign": "center",
                            "justify-content": "center",
                            "min-width": "210px",
                        },
                    )
                ],
                style={"display": "flex", "justify-content": "center"},
            ),
        ]

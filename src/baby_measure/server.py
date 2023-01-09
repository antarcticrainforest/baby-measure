"""Module containing all dash server callback methods."""

from __future__ import annotations
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, cast

import pandas as pd
from dash import (
    ctx,
    Dash,
    dcc,
    dash_table,
    exceptions,
    html,
    Input,
    Output,
    State,
)
from .utils import (
    logger,
    DBSettings,
    set_date_picker,
    str_to_timestamp,
)
from .edit import Edit
from .plot import Plot
from .github import GHPages

db_settings = DBSettings()
gh_page = GHPages(db_settings)
plot = Plot(db_settings, gh_page)
edit = Edit(db_settings)
app = Dash(
    "baby-measurement",
    assets_folder=Path(__file__).parent / "assets",
    title="Baby Measure",
)
app._favicon = Path(__file__).parent / "assets" / "favicon.ico"


@app.callback(
    Output("mamadera-timepicker", component_property="children"),
    Input("mamadera-now-button", component_property="n_clicks"),
)
def set_mamadera_now(n_clicks: int) -> list:
    """Set the mamadera time to the current datetime."""
    return set_date_picker("mamadera")


@app.callback(
    Output("saca_leche-timepicker", component_property="children"),
    Input("saca_leche-now-button", component_property="n_clicks"),
)
def set_sace_leche_now(n_clicks: int) -> list:
    """Set the mamadera time to the current datetime."""
    return set_date_picker("saca_leche")


@app.callback(
    Output("leche-timepicker", component_property="children"),
    Input("leche-now-button", component_property="n_clicks"),
)
def set_leche_now(n_clicks: int) -> list:
    """Set the mamadera time to the current datetime."""
    return set_date_picker("leche")


@app.callback(
    Output("body-timepicker", component_property="children"),
    Input("body-now-button", component_property="n_clicks"),
)
def set_body_now(n_clicks: int) -> list:
    """Set the mamadera time to the current datetime."""
    return set_date_picker("body")


@app.callback(
    Output("nappy-timepicker", component_property="children"),
    Input("nappy-now-button", component_property="n_clicks"),
)
def set_nappy_now(n_clicks: int) -> list:
    """Set the mamadera time to the current datetime."""
    return set_date_picker("nappy")


@app.callback(
    Output("plot-tab", component_property="children"),
    Input("submit-button", component_property="n_clicks"),
    Input("edit-entries", component_property="n_clicks"),
)
def refresh_plot(*args) -> list:
    return plot.children


@app.callback(
    Output("measure-tab", component_property="children"),
    State("mamadera-amount", component_property="value"),
    State("mamadera-timepicker-obj", component_property="date"),
    State("leche-amount", component_property="value"),
    State("saca_leche-timepicker-obj", component_property="date"),
    State("leche-dur", component_property="value"),
    State("leche-timepicker-obj", component_property="date"),
    State("weight", component_property="value"),
    State("head", component_property="value"),
    State("length", component_property="value"),
    State("body-timepicker-obj", component_property="date"),
    State("nappy-content", component_property="value"),
    State("nappy-timepicker-obj", component_property="date"),
    State("measure-tab", component_property="children"),
    Input("submit-button", component_property="n_clicks"),
)
def log_entries(
    mamadera_amount: int,
    mamadera_time: str,
    leche_amount: int,
    leche_time: str,
    leche_dur: int,
    leche_dur_time: str,
    weight: int,
    head: int,
    length: int,
    body_time: str,
    nappy_content: str,
    nappy_time: str,
    components: list,
    n_clicks: int,
) -> list:
    """Log all entries."""
    entries = {
        "mamadera_amount": mamadera_amount,
        "leche_amount": leche_amount,
        "leche_duration": leche_dur,
        "weight": weight,
        "head": head,
        "length": length,
        "nappy_content": nappy_content,
    }
    times = {
        "body": str_to_timestamp(body_time),
        "mamadera_formula": str_to_timestamp(mamadera_time),
        "mamadera_leche": str_to_timestamp(leche_time),
        "leche": str_to_timestamp(leche_dur_time),
        "nappy": str_to_timestamp(nappy_time),
    }
    if n_clicks > 0:
        db_settings.log_entries(entries, times)
    gh_page.commit()
    tab = db_settings.add_entry_tab()
    return tab


@app.callback(
    Output("edit-tab", component_property="children"),
    State("edit-formula-index-select", component_property="value"),
    State("edit-formula-field", component_property="value"),
    State("edit-milk-index-select", component_property="value"),
    State("edit-milk-field", component_property="value"),
    State("edit-feeding-index-select", component_property="value"),
    State("edit-feeding-field", component_property="value"),
    State("edit-weight-index-select", component_property="value"),
    State("edit-weight-field", component_property="value"),
    State("edit-height-index-select", component_property="value"),
    State("edit-height-field", component_property="value"),
    State("edit-head-index-select", component_property="value"),
    State("edit-head-field", component_property="value"),
    State("edit-nappy-index-select", component_property="value"),
    State("edit-nappy-field", component_property="value"),
    State("edit-action", component_property="value"),
    Input("edit-entries", component_property="n_clicks"),
    Input("submit-button", component_property="n_clicks"),
)
def edit_values(
    formula_index: None | int,
    formula_amount: None | int,
    milk_index: None | int,
    milk_amount: None | int,
    feeding_index: None | int,
    feeding_amount: None | int,
    weight_index: None | int,
    weight_amount: None | int,
    height_index: None | int,
    height_amount: None | int,
    head_index: None | int,
    head_amount: None | int,
    nappy_index: None | int,
    nappy_content: None | str,
    action: str,
    *args: int,
) -> list[html.Div]:
    tables = [
        ("mamadera", formula_index, {"amount": formula_amount}),
        ("mamadera", milk_index, {"amount": milk_amount}),
        ("breastfeeding", feeding_index, {"duration": feeding_amount}),
        ("nappie", nappy_index, {"type": nappy_content}),
    ]
    for (table, index, value) in tables:
        edit.alter_table(table, index, value, action)
    children = edit.children
    gh_page.commit()
    return children

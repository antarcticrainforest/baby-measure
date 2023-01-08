"""Definitions of the dash layout."""

from __future__ import annotations

from dash import html, dcc
from .server import db_settings, plot, edit


measure_tab = [
    html.Div(id="measure-tab", children=db_settings.add_entry_tab())
]
plot_tab = [html.Div(id="plot-tab", children=plot.children)]
edit_tab = [html.Div(id="edit-tab", children=edit.children)]

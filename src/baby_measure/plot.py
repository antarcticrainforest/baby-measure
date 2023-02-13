"""Module to plot data."""

from __future__ import annotations
from datetime import datetime
from pathlib import Path
import time
from typing import Tuple, Optional

import appdirs
from dash import html, dcc
from plotly import express as px
import plotly
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from .utils import DBSettings


class Plot:
    """All plots on one page."""

    def __init__(self, db_settings: DBSettings):

        self.db_settings = db_settings

    def read_db(self, table: str) -> pd.DataFrame:
        return self.db_settings.read_db(table)

    def amount(self, times: Optional[Tuple[datetime, datetime]] = None):
        """Create the amount plot."""
        entries = self.read_db("mamadera")
        fig = px.line(
            entries,
            y="amount",
            x="time",
            color="type",
            markers=True,
        )
        fig.update_traces(line=dict(width=3), marker=dict(size=10))
        fig.update_layout(
            yaxis_title="Amount [ml]",
            xaxis_title="",
            xaxis=dict(rangeslider=dict(visible=True)),
            dragmode="pan",
            margin=dict(l=10, r=10, b=20),
            title="Bottle feeding",
            legend=dict(
                font=dict(size=14),
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                title="",
                orientation="h",
            ),
        )
        fig.update_xaxes(
            range=times or self.get_xaxis_range(entries.time),
            fixedrange=False,
        )
        return fig

    def get_xaxis_range(self, times: pd.Series) -> list[pd.Timestamp]:
        """Get the time range to be displayed."""
        datetimes = pd.DatetimeIndex(times).sort_values()
        dt = datetime.now() - datetimes
        times = datetimes[dt <= pd.Timedelta(days=10)]
        if len(times) == 0:
            return datetimes[0], datetimes[-1]
        if len(times) == 1:
            return max(datetimes[0], times[0]), min(datetimes[-1], times[0])
        return [
            times[0] - pd.Timedelta(hours=12),
            times[-1] + pd.Timedelta(hours=12),
        ]

    def breastfeeding(self, times: Optional[Tuple[datetime, datetime]] = None):

        entries = self.read_db("breastfeeding")
        if not len(entries):
            return None
        entries.index = entries.time
        dur = entries["duration"].groupby(pd.Grouper(freq="1D")).sum()
        data = pd.DataFrame({"duration": dur, "time": dur.index})
        data.index = list(range(len(data)))
        fig = px.bar(
            data.sort_values("time"),
            x="time",
            y="duration",
            title="Breast feeding",
        )
        fig.update_layout(
            yaxis_title="Duration [min]",
            xaxis_title="",
            xaxis=dict(rangeslider=dict(visible=True)),
            dragmode="pan",
            margin=dict(l=10, r=10, b=20),
            legend=dict(
                font=dict(size=14),
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                title="",
                orientation="h",
            ),
        )
        fig.update_xaxes(
            range=times or self.get_xaxis_range(data.time),
            fixedrange=False,
        )
        return fig

    def daily_amount(self, times: Optional[Tuple[datetime, datetime]] = None):

        entries = self.read_db("mamadera")
        if not len(entries):
            return None
        entries.index = entries.time

        formula = (
            entries.loc[entries.type == "formula"]["amount"]
            .groupby(pd.Grouper(freq="1D"))
            .sum()
        )
        breastmilk = (
            entries.loc[entries.type == "breastmilk"]["amount"]
            .groupby(pd.Grouper(freq="1D"))
            .sum()
        )
        formula = pd.DataFrame(
            {
                "amount": formula,
                "time": formula.index,
                "type": len(formula) * ["formula"],
            }
        )
        milk = pd.DataFrame(
            {
                "amount": breastmilk,
                "time": breastmilk.index,
                "type": len(breastmilk) * ["breastmilk"],
            }
        )
        data = pd.concat([formula, milk])
        data.index = list(range(len(data)))
        fig = px.bar(
            data.sort_values("time"),
            x="time",
            y="amount",
            color="type",
            title="Daily Bottle Intake",
        )
        fig.update_layout(
            yaxis_title="Amount [ml]",
            xaxis_title="",
            xaxis=dict(rangeslider=dict(visible=True)),
            dragmode="pan",
            margin=dict(l=10, r=10, b=20),
            legend=dict(
                font=dict(size=14),
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                title="",
                orientation="h",
            ),
        )
        fig.update_xaxes(
            range=times or self.get_xaxis_range(data.time),
            fixedrange=False,
        )
        return fig

    def create_body_sub_plot(self):

        entries = self.read_db("body")

        fig = make_subplots(rows=3, cols=1)
        for n, key in enumerate(("Weight [kg]", "Height [cm]", "Head size [cm]")):
            prop = key.split()[0]
            entry = entries[["time", prop.lower()]].dropna()
            fig.append_trace(
                go.Scatter(
                    x=entry["time"],
                    y=entry[prop.lower()],
                    name=prop,
                ),
                row=n + 1,
                col=1,
            )
            fig.update_yaxes(title_text=key, row=n + 1, col=1)
        fig.update_layout(
            title_text="Body measures",
            margin=dict(l=10, r=10, b=20),
            legend=dict(
                yanchor="bottom",
                y=1.02,
                font=dict(size=14),
                xanchor="right",
                x=1,
                title="",
                orientation="h",
            ),
        )
        return fig

    def plot_body(self, prop: str, label: str, title: str):
        """Plot body measurment."""
        entries = self.read_db("body")
        fig = px.line(
            entries[["time", prop]].dropna(),
            y=prop,
            x="time",
            markers=True,
        )
        fig.update_traces(line=dict(width=3), marker=dict(size=10))
        fig.update_layout(
            yaxis_title=label,
            xaxis_title="",
            title=title,
            dragmode="pan",
            margin=dict(l=10, r=10, b=20),
            xaxis=dict(rangeslider=dict(visible=True)),
        )
        return fig

    def nappy(self, times: Optional[Tuple[datetime, datetime]] = None):

        entries = self.read_db("nappie")
        if not len(entries):
            return None
        entries["count"] = len(entries) * [1]
        entries.index = entries.time
        poop = (
            entries.loc[entries.type == "poop"]["count"]
            .groupby(pd.Grouper(freq="1D"))
            .sum()
        )
        pee = (
            entries.loc[entries.type == "pee"]["count"]
            .groupby(pd.Grouper(freq="1D"))
            .sum()
        )
        pee = pd.DataFrame(
            {
                "count": pee,
                "time": pee.index,
                "type": len(pee) * ["Pee"],
            }
        )
        poop = pd.DataFrame(
            {
                "count": poop,
                "time": poop.index,
                "type": len(poop) * ["Poop"],
            }
        )
        data = pd.concat([pee, poop])
        data.index = list(range(len(data)))
        try:
            last_poo = entries.loc[entries.type == "poop"].iloc[-1]["time"]
            add = f'(last Poop: {last_poo.strftime("%a %R")})'
        except IndexError:
            add = ""
        fig = px.bar(
            data.sort_values("time"),
            x="time",
            y="count",
            color="type",
            title=f"Nappy content {add}",
        )
        fig.update_layout(
            yaxis_title="Nappy count",
            xaxis_title="",
            xaxis=dict(rangeslider=dict(visible=True)),
            dragmode="pan",
            margin=dict(l=10, r=10, b=20),
            legend=dict(
                yanchor="bottom",
                y=1.02,
                font=dict(size=14),
                xanchor="right",
                x=1,
                title="",
                orientation="h",
            ),
        )
        fig.update_xaxes(
            range=self.get_xaxis_range(data.time),
            fixedrange=False,
        )
        return fig

    @property
    def children(self) -> list:
        """Create a div container."""
        total_amount_fig = self.amount()
        daily_amount_fig = self.daily_amount()
        breastfeeding_fig = self.breastfeeding()
        weight_fig = self.plot_body("weight", "Weight [km]", "Body Weight")
        height_fig = self.plot_body("height", "Height [cm]", "Body Height")
        head_fig = self.plot_body("head", "Size [cm]", "Head Size")
        nappy_fig = self.nappy()
        return [
            html.Div(
                id="amounts",
                children=[
                    dcc.Graph(
                        id="amounts-plot",
                        figure=total_amount_fig,
                        config={"displaylogo": False},
                    )
                ],
            ),
            html.Div(
                id="daily-amount",
                children=[
                    dcc.Graph(
                        id="daily-amounts-plot",
                        figure=daily_amount_fig,
                        config={"displaylogo": False},
                    )
                ],
            ),
            html.Div(
                id="feeding-dur",
                children=[
                    dcc.Graph(
                        id="feeding-dur-plot",
                        figure=breastfeeding_fig,
                        config={"displaylogo": False},
                    ),
                ],
            ),
            html.Div(
                id="body-plots",
                children=[
                    dcc.Graph(
                        id="weight-plot",
                        figure=weight_fig,
                        config={"displaylogo": False},
                    ),
                    dcc.Graph(
                        id="height-plot",
                        figure=height_fig,
                        config={"displaylogo": False},
                    ),
                    dcc.Graph(
                        id="head-plot",
                        figure=head_fig,
                        config={"displaylogo": False},
                    ),
                ],
            ),
            html.Div(
                id="nappy-stat",
                children=[
                    dcc.Graph(
                        id="nappy-plot",
                        figure=nappy_fig,
                        config={"displaylogo": False},
                    )
                ],
            ),
        ]

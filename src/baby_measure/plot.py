"""Module to plot data."""

from __future__ import annotations
from datetime import datetime
from pathlib import Path
import time

import appdirs
from dash import html, dcc
from plotly import express as px
import plotly
import pandas as pd

from .utils import DBSettings
from .github import GHPages


class Plot:
    """All plots on one page."""

    def __init__(self, db_settings: DBSettings, pages: GHPages):

        self.db_settings = db_settings
        self.gh_pages = pages

    def read_db(self, table: str) -> pd.DataFrame:
        return self.db_settings.read_db(table)

    @property
    def amount(self):
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
            range=self.get_xaxis_range(entries.time),
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

    @property
    def breastfeeding(self):

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
            range=self.get_xaxis_range(data.time),
            fixedrange=False,
        )
        return fig

    @property
    def daily_amount(self):

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
            range=self.get_xaxis_range(data.time),
            fixedrange=False,
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

    @property
    def nappy(self):

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

    def save_plots(
        self, *figs: plotly.graph_objs._figure.Figure
    ) -> Path | None:
        cache_dir = self.gh_pages.repo_dir
        out_file = self.gh_pages.repo_dir / "index.html"
        if out_file.is_file() and (
            time.time() - out_file.stat().st_mtime < 60
        ):
            return
        header = "<html><head><title>Baby Measure</title>"
        header += '<link rel="icon" type="image/x-icon" href="favicon.ico">'
        header += "</head><body>"
        for fig in figs:
            header += fig.to_html(full_html=False)
        header += "</body></html>"
        cache_dir.mkdir(parents=True, exist_ok=True)
        with out_file.open("w", encoding="utf-8") as f_obj:
            f_obj.write(header)
        print(f"Plots saved to {cache_dir / 'index.html'}")

    @property
    def children(self) -> list:
        """Create a div container."""
        total_amount_fig = self.amount
        daily_amount_fig = self.daily_amount
        breastfeeding_fig = self.breastfeeding
        weight_fig = self.plot_body("weight", "Weight [km]", "Body Weight")
        height_fig = self.plot_body("height", "Height [cm]", "Body Height")
        head_fig = self.plot_body("head", "Size [cm]", "Head Size")
        nappy_fig = self.nappy
        self.save_plots(
            total_amount_fig,
            daily_amount_fig,
            breastfeeding_fig,
            weight_fig,
            height_fig,
            height_fig,
            nappy_fig,
        )
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

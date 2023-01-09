"""Server app running the baby measurments."""
from __future__ import annotations
import argparse
from pathlib import Path
import json

from dash import Dash, dcc, html
import dash_loading_spinners as dls

from .layout import measure_tab, plot_tab, edit_tab
from .server import app, DBSettings

__version__ = "0.1.0"


def cli() -> None:
    """Construct the command line interface."""

    cli_app = argparse.ArgumentParser(
        prog="baby-measure",
        description="View and manipulate geojson files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    cli_app.add_argument("--debug", action="store_true", default=False)
    cli_app.add_argument(
        "--port",
        type=int,
        default=8050,
        help="The port the app should be running on.",
    )
    cli_app.add_argument(
        "-V",
        "--version",
        action="version",
        version="%(prog)s {version}".format(version=__version__),
    )
    cli_app.add_argument(
        "-c",
        "--config",
        "--configure",
        action="store_true",
        default=False,
        help="Only (re)-configure the app.",
    )
    args = cli_app.parse_args()
    if args.config:
        DBSettings.configure(override=True)
        return
    run_server(debug_mode=args.debug, port=args.port)


def run_server(
    debug_mode: bool = False, port: int = 8050, run_server=True, **kwargs: str
) -> None:
    """Set up and run the server serving the baby measurement app.

    This server will serve a dash app running on localhost. Currently only
    the development mode of the server is supported.

    Parameters
    ----------
    debug_mode: bool, defautl: True
        Run server in debug mode.
    port: int, default: 5002
        The port the server application in running on.
    kwargs:
        Additional keyword arguments
    """
    _ = DBSettings.configure()
    app.layout = html.Div(
        children=[
            dcc.Tabs(
                [
                    dcc.Tab(
                        label="New Entries",
                        children=[
                            dls.Hash(
                                html.Div(id="display", children=measure_tab),
                            )
                        ],
                    ),
                    dcc.Tab(
                        label="Analytics",
                        children=[dls.Hash(html.Div(id="plot", children=plot_tab))],
                    ),
                    dcc.Tab(
                        label="Edit Entries",
                        children=[dls.Hash(html.Div(id="edit", children=edit_tab))],
                    ),
                ]
            )
        ]
    )
    if run_server:
        app.run_server(debug=debug_mode, port=str(port), host="0.0.0.0")
    return app


if __name__ == "__main__":
    cli()

"""Server app running the baby measurments."""
from __future__ import annotations
import asyncio
import threading
from typing import Any, Callable


from dash import Dash, dcc, html
import dash_loading_spinners as dls

from .utils import DBSettings


def run_flask_server(
    debug_mode: bool = False, port: int = 5080, **kwargs: str
) -> None:
    """Set up and run the flask server serving the baby measurement app.

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
    from .layout import measure_tab, plot_tab, edit_tab
    from .server import app, gh_page, server

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
                        children=[
                            dls.Hash(html.Div(id="plot", children=plot_tab))
                        ],
                    ),
                    dcc.Tab(
                        label="Edit Entries",
                        children=[
                            dls.Hash(html.Div(id="edit", children=edit_tab))
                        ],
                    ),
                ]
            )
        ]
    )
    gh_page.debug = debug_mode
    server.run(debug=debug_mode, port=str(port), host="0.0.0.0")


def run_telegram(token: str, port: int = 8050):
    from telepot.aio.loop import MessageLoop
    from .telegram import Telegram

    return
    loop = asyncio.get_event_loop()
    bot = Telegram.bot_from_token(token, port=port)
    loop.create_task(MessageLoop(bot).run_forever())
    loop.run_forever()


def run_server(
    debug_mode: bool = False, port: int = 8050, run_server=True, **kwargs: str
) -> None:
    """Set up and run the services for running the server.

    Depending on the configuration this will just run the flask server for
    serving the web site or also a service communicating with the REST API
    to log and get entries via SMS and a Telegram bot.

    Parameters
    ----------
    debug_mode: bool, defautl: True
        Run server in debug mode.
    port: int, default: 5002
        The port the server application in running on.
    kwargs:
        Additional keyword arguments
    """

    db_settings = DBSettings.configure()
    token = db_settings.get("tg_token")
    proc = []
    proc.append(mp.Process(target=run_flask_server, args=(debug_mode, port)))
    if token:
        proc.append(mp.Process(target=run_telegram, args=(token, port)))
    for p in proc:
        p.start()
    [p.join() for p in proc]

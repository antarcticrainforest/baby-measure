"""Command line interface for the baby measure app."""
from __future__ import annotations
import argparse
import multiprocessing as mp

from .utils import DBSettings
from ._version import __version__


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
    cli_app.add_argument(
        "-t",
        "--telegram",
        "--telegram-bot",
        action="store_true",
        default=False,
        help="Run only the telegram chat-bot",
    )
    args = cli_app.parse_args()
    if args.config:
        DBSettings.configure(override=True)
        return
    from .app import run_flask_server, run_telegram

    token = DBSettings.configure().get("tg_token")
    if token:
        tele_g = mp.Process(target=run_telegram, args=(token, args.port))
        tele_g.start()
    run_flask_server(debug_mode=args.debug, port=args.port)

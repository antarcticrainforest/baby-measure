"""Command line interface for the baby measure app."""
from __future__ import annotations
import argparse
import multiprocessing as mp
import os
import appdirs
from .utils import DBSettings
from ._version import __version__


def cli() -> None:
    """Construct the command line interface."""
     db_settings_file = (
            Path(appdirs.user_config_dir()) / "baby-measure" / "db_config.json"
    )
    db_settings_file = Path(
        os.environ.get("CONFIG_FILE", db_settings_file) or db_settings_file
    )
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
        "-r",
        "--reconfigure",
        action="store_true",
        default=False,
        help="Only (re)-configure the app.",
    )
    cli_app.add_argument(
        "-c",
        "--config",
        type=Path,
        default=db_settings_file
    )
    cli_app.add_argument(
        "-s",
        "--services",
        nargs="+",
        type=str,
        default=["web", "telegram"],
        choices=["web", "telegram", "sms"],
        help="Set the services you want to run.",
    )
    args = cli_app.parse_args()
    os.environ["CONFIG_FILE"] = str(args.config)
    if args.config:
        DBSettings.configure(override=True)
        return
    from .app import run_flask_server, run_telegram

    token = DBSettings.configure().get("tg_token")
    background_proc = []
    if token and "telegram" in args.services:
        background_proc.append(
            mp.Process(target=run_telegram, args=(token, args.port))
        )
        background_proc[-1].start()
    if "web" in args.services:
        run_flask_server(debug_mode=args.debug, port=args.port)
    for proc in background_proc:
        proc.join()

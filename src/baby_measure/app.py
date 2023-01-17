"""Server app running the baby measurments."""
from __future__ import annotations

from dash import Dash, dcc, html
import dash_loading_spinners as dls


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
    from .layout import measure_tab, plot_tab, edit_tab
    from .server import app, DBSettings, gh_page, server

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
    if run_server:
        gh_page.debug = debug_mode
        app.run(debug=debug_mode, port=str(port), host="0.0.0.0")
    return app


if __name__ == "__main__":
    cli()

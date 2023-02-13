from .utils import DBSettings
from .plot import Plot


db_settings = DBSettings()
plot = Plot(db_settings)

from .utils import DBSettings
from .plot import Plot
from .github import GHPages


db_settings = DBSettings()
gh_page = GHPages(db_settings)
plot = Plot(db_settings, gh_page)

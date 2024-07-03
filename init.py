from vnncomp.main import app
from vnncomp.utils.settings import Settings

with app.app_context():
    Settings.init()

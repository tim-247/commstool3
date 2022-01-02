from flask import Flask

from flaskapp.config import Config

app = Flask(__name__)
app.config.from_object(Config)

from flaskapp import routes  # noqa: F401, E402

from flask import jsonify, Flask, request
from app.logger import get_logger
from flask_cors import CORS
from app.server.errors import init_handler
from app.server.api_controller import main_api_controller

app = Flask(__name__)
CORS(
    app,
    origins=["http://localhost:5173"],
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
init_handler(app)


@app.route("/profiles")
def profiles():
    return main_api_controller.get_profiles()


@app.route("/stop-all", methods=["POST"])
def stop_all():
    main_api_controller.stop_all()
    return {}


@app.route("/start-all", methods=["POST"])
def start():
    x = main_api_controller.start_all()
    if x is None:
        return {}
    return x


@app.route("/start-selected", methods=["POST"])
def start_selected():
    x = main_api_controller.start_selected()
    if x is None:
        return {}
    return x


@app.route("/status")
def status():
    return main_api_controller.status()()

srv_app = app

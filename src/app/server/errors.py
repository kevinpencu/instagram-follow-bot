from flask import jsonify, json, make_response
from werkzeug.exceptions import HTTPException


def init_handler(app):
    @app.errorhandler(Exception)
    def handle_exception(e):
        if isinstance(e, HTTPException):
            response = e.get_response()
            response.data = json.dumps(
                {
                    "code": e.code,
                    "name": e.name,
                    "description": e.description,
                }
            )
        else:
            response = make_response(
                jsonify({"message": "Something went wrong"}), 500
            )

        response.headers["Access-Control-Allow-Origin"] = "*"
        response.content_type = "application/json"
        return response

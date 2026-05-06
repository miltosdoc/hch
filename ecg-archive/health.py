"""Health check endpoint for Docker."""
from flask import jsonify

def register(app):
    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

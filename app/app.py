import os
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template

app = Flask(__name__)
APP_VERSION = os.environ.get("APP_VERSION", "local")
STARTED_AT = datetime.now(timezone.utc).isoformat(timespec="seconds")


@app.get("/")
def home():
    return render_template("index.html", version=APP_VERSION, started_at=STARTED_AT)


@app.get("/health")
def health():
    return jsonify(status="ok", version=APP_VERSION), 200


@app.get("/api/status")
def status():
    return jsonify(
        service="cloudops-delivery-guard",
        status="operational",
        version=APP_VERSION,
        started_at=STARTED_AT,
        checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    ), 200

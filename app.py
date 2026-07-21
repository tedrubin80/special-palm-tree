"""Serve the MediaSearch project showcase (search UI retired)."""

from pathlib import Path

from flask import Flask, send_from_directory

DEMO_DIR = Path(__file__).parent / "demo"

app = Flask(__name__, static_folder=None)


@app.route("/")
def home():
    return send_from_directory(DEMO_DIR, "index.html")


@app.route("/data.json")
def data():
    return send_from_directory(DEMO_DIR, "data.json")


@app.route("/demo/")
@app.route("/demo/<path:filename>")
def demo_files(filename="index.html"):
    return send_from_directory(DEMO_DIR, filename)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

from flask import Flask, render_template, request
import os

from main import run   # albo Twój analyzer

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():

    file = request.files["csv"]

    path = os.path.join("uploads", "ecg.csv")
    file.save(path)

    result = run(path)

    return render_template(
        "result.html",
        results=result["results"]
    )


if __name__ == "__main__":
    app.run(debug=True)
import os
from uuid import uuid4

from flask import Flask, flash, redirect, render_template, request, url_for
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from config import ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_MB, PLOTS_FOLDER, UPLOAD_FOLDER
from main import run


app = Flask(__name__)
app.config.update(
    MAX_CONTENT_LENGTH=MAX_UPLOAD_SIZE_MB * 1024 * 1024,
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "local-development-key"),
)

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
PLOTS_FOLDER.mkdir(parents=True, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files.get("csv")
    if file is None or not file.filename:
        flash("Wybierz plik CSV z zapisem EKG.", "error")
        return redirect(url_for("index"))

    if not allowed_file(file.filename):
        flash("Dozwolone są wyłącznie pliki CSV lub TXT.", "error")
        return redirect(url_for("index"))

    original_name = secure_filename(file.filename)
    analysis_id = uuid4().hex
    path = UPLOAD_FOLDER / f"{analysis_id}_{original_name}"
    file.save(path)

    plot_filename = f"plots/ecg_{analysis_id}.png"
    try:
        result = run(path, plot_path=PLOTS_FOLDER / f"ecg_{analysis_id}.png")
    except Exception:
        app.logger.exception("ECG analysis failed")
        path.unlink(missing_ok=True)
        flash("Nie udało się przeanalizować pliku. Sprawdź jego format i dane.", "error")
        return redirect(url_for("index"))

    return render_template(
        "result.html",
        results=result["results"],
        sampling_rate=result["sampling_rate"],
        r_peak_count=len(result["r_peaks"]),
        plot_url=url_for("static", filename=plot_filename),
    )


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(_error):
    flash(f"Plik jest zbyt duży. Maksymalny rozmiar to {MAX_UPLOAD_SIZE_MB} MB.", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")

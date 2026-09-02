import json
import os
import re
from io import BytesIO
from datetime import datetime, timezone
from uuid import uuid4

from flask import Flask, abort, flash, redirect, render_template, request, send_file, url_for
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from config import ANALYSIS_FOLDER, ALLOWED_EXTENSIONS, ECG_CHUNK_ROWS, MAX_UPLOAD_SIZE_MB, PLOTS_FOLDER, UPLOAD_FOLDER
from io_utils import load_ecg_time_range
from leads import build_standard_12_leads
from main import run
from preprocessing import preprocess
from rpeaks import get_rpeaks
from visualization import plot_12_lead_ecg, plot_ecg, plot_event_review


REVIEW_STATUSES = {
    "unreviewed": "Do weryfikacji",
    "confirmed": "Potwierdzone",
    "rejected": "Odrzucone",
    "artifact": "Artefakt",
    "uncertain": "Niejednoznaczne",
}
ANALYSIS_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


app = Flask(__name__)
app.config.update(
    MAX_CONTENT_LENGTH=MAX_UPLOAD_SIZE_MB * 1024 * 1024,
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "local-development-key"),
)

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
PLOTS_FOLDER.mkdir(parents=True, exist_ok=True)
ANALYSIS_FOLDER.mkdir(parents=True, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _manifest_path(analysis_id):
    if not ANALYSIS_ID_PATTERN.fullmatch(analysis_id):
        abort(404)
    return ANALYSIS_FOLDER / f"{analysis_id}.json"


def _load_manifest(analysis_id):
    try:
        return json.loads(_manifest_path(analysis_id).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        abort(404)


def _save_manifest(manifest):
    _manifest_path(manifest["analysis_id"]).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _events_for_manifest(events):
    prepared = []
    for index, event in enumerate(events, start=1):
        prepared.append(
            {
                **event,
                "event_id": f"event-{index}",
                "review_status": "unreviewed",
                "review_note": "",
                "reviewed_at": None,
            }
        )
    return prepared


def _event_from_manifest(manifest, event_id):
    event = next(
        (candidate for candidate in manifest.get("event_contexts", []) if candidate.get("event_id") == event_id),
        None,
    )
    if event is None:
        abort(404)
    return event


def _render_analysis_result(manifest):
    analysis_id = manifest["analysis_id"]
    return render_template(
        "result.html",
        analysis_id=analysis_id,
        events=manifest.get("event_contexts", []),
        event_summary=tuple(manifest.get("report", {}).get("candidate_counts", {}).items()),
        report=manifest.get("report", {}),
        warnings=manifest.get("warnings", []),
        sampling_rate=manifest["sampling_rate"],
        r_peak_count=manifest.get("r_peak_count", 0),
        duration_seconds=manifest["duration_seconds"],
        record_start_time=manifest.get("start_time", 0.0),
        strip_url=url_for("analysis_strip", analysis_id=analysis_id),
        plot_url=url_for("static", filename=f"plots/ecg_{analysis_id}.png"),
        is_twelve_lead=manifest.get("is_twelve_lead", False),
        analysis_lead=manifest["analysis_lead"],
        recorded_leads=manifest.get("recorded_leads", ()),
        review_statuses=REVIEW_STATUSES,
    )


@app.route("/")
def index():
    return render_template("index.html", max_upload_mb=MAX_UPLOAD_SIZE_MB)


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

    try:
        result = run(
            path,
            plot_path=PLOTS_FOLDER / f"ecg_{analysis_id}.png",
        )
    except Exception:
        app.logger.exception("ECG analysis failed")
        flash("Nie udało się przeanalizować pliku. Zapis źródłowy pozostawiono do weryfikacji formatu i jakości danych.", "error")
        return redirect(url_for("index"))

    manifest = {
        "analysis_id": analysis_id,
        "source_file": path.name,
        "sampling_rate": result["sampling_rate"],
        "start_time": result["start_time"],
        "end_time": result["end_time"],
        "duration_seconds": result["duration_seconds"],
        "r_peak_count": result["r_peak_count"],
        "is_twelve_lead": result["is_twelve_lead"],
        "analysis_lead": result["analysis_lead"],
        "recorded_leads": result["recorded_leads"],
        "warnings": result["warnings"],
        "report": result["report"],
        "event_contexts": _events_for_manifest(result["event_contexts"]),
    }
    try:
        _save_manifest(manifest)
    except OSError:
        app.logger.exception("Could not persist ECG analysis manifest")
        flash("Analiza została wykonana, ale nie udało się zapisać indeksu kontekstów.", "error")

    return _render_analysis_result(manifest)


@app.route("/analysis/<analysis_id>")
def analysis_result(analysis_id):
    return _render_analysis_result(_load_manifest(analysis_id))


@app.route("/analysis/<analysis_id>/strip")
def analysis_strip(analysis_id):
    """Render a requested rhythm strip without sending the whole Holter to the browser."""
    manifest = _load_manifest(analysis_id)
    source_path = UPLOAD_FOLDER / manifest["source_file"]
    if source_path.name != manifest["source_file"] or not source_path.is_file():
        abort(404)

    duration = float(manifest["duration_seconds"])
    record_start = float(manifest.get("start_time", 0.0))
    try:
        requested_offset = float(request.args.get("offset", 0))
        requested_window = float(request.args.get("window", 30))
    except ValueError:
        abort(400)
    window = min(max(requested_window, 2.0), min(120.0, duration))
    offset = min(max(requested_offset, 0.0), max(0.0, duration - window))
    start_time = record_start + offset
    end_time = start_time + window

    try:
        _schema, time, signals = load_ecg_time_range(source_path, start_time, end_time, ECG_CHUNK_ROWS)
        raw_ecg = signals[manifest["analysis_lead"]]
        cleaned_ecg = preprocess(raw_ecg, manifest["sampling_rate"])
        r_peaks = get_rpeaks(cleaned_ecg, manifest["sampling_rate"])
    except (OSError, ValueError):
        app.logger.exception("Could not render ECG strip")
        abort(500)

    visible_events = [
        event
        for event in manifest.get("event_contexts", [])
        if event["start_time"] <= end_time and event["end_time"] >= start_time
    ]
    image = BytesIO()
    plot_ecg(time, cleaned_ecg, r_peaks, visible_events, output_path=image, lead_name=manifest["analysis_lead"])
    image.seek(0)
    return send_file(image, mimetype="image/png", max_age=0)


@app.route("/analysis/<analysis_id>/events/<event_id>")
def event_review(analysis_id, event_id):
    manifest = _load_manifest(analysis_id)
    event = _event_from_manifest(manifest, event_id)
    source_path = UPLOAD_FOLDER / manifest["source_file"]
    if source_path.name != manifest["source_file"] or not source_path.is_file():
        abort(404)

    try:
        _schema, time, recorded_leads = load_ecg_time_range(
            source_path,
            event["context_start"],
            event["context_end"],
            ECG_CHUNK_ROWS,
        )
        leads = build_standard_12_leads(recorded_leads) if manifest["is_twelve_lead"] else recorded_leads
        rhythm_lead = manifest["analysis_lead"]
        raw_ecg = leads[rhythm_lead]
        cleaned_ecg = preprocess(raw_ecg, manifest["sampling_rate"])
        r_peaks = get_rpeaks(cleaned_ecg, manifest["sampling_rate"])
    except (OSError, ValueError):
        app.logger.exception("Could not build ECG event review")
        abort(500)

    event_plot_filename = f"plots/review_{analysis_id}_{event_id}.png"
    plot_event_review(
        time,
        raw_ecg,
        cleaned_ecg,
        r_peaks,
        event,
        PLOTS_FOLDER / f"review_{analysis_id}_{event_id}.png",
        rhythm_lead,
    )

    twelve_lead_plot_url = None
    if manifest["is_twelve_lead"]:
        twelve_lead_plot_filename = f"plots/review_12lead_{analysis_id}_{event_id}.png"
        plot_12_lead_ecg(
            time,
            leads,
            PLOTS_FOLDER / f"review_12lead_{analysis_id}_{event_id}.png",
            overview_seconds=float(time[-1] - time[0]),
            event_time=event["start_time"],
            event_label=event["name"],
        )
        twelve_lead_plot_url = url_for("static", filename=twelve_lead_plot_filename)

    return render_template(
        "event_review.html",
        analysis_id=analysis_id,
        event=event,
        review_statuses=REVIEW_STATUSES,
        event_plot_url=url_for("static", filename=event_plot_filename),
        twelve_lead_plot_url=twelve_lead_plot_url,
        rhythm_lead=rhythm_lead,
        context_duration_seconds=float(time[-1] - time[0]),
    )


@app.route("/analysis/<analysis_id>/events/<event_id>/review", methods=["POST"])
def update_event_review(analysis_id, event_id):
    manifest = _load_manifest(analysis_id)
    event = _event_from_manifest(manifest, event_id)
    status = request.form.get("review_status", "")
    if status not in REVIEW_STATUSES:
        abort(400)

    event["review_status"] = status
    event["review_note"] = request.form.get("review_note", "").strip()[:1000]
    event["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    try:
        _save_manifest(manifest)
    except OSError:
        app.logger.exception("Could not persist ECG event review")
        flash("Nie udało się zapisać oznaczenia przeglądu.", "error")
    else:
        flash("Oznaczenie zdarzenia zapisano.", "success")
    return redirect(url_for("event_review", analysis_id=analysis_id, event_id=event_id))


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(_error):
    flash(f"Plik jest zbyt duży. Maksymalny rozmiar to {MAX_UPLOAD_SIZE_MB} MB.", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")

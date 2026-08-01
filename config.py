from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

# Used only when a sampling rate cannot be inferred from the first CSV column.
FS = 500
MAX_UPLOAD_SIZE_MB = 20
UPLOAD_FOLDER = BASE_DIR / "uploads"
PLOTS_FOLDER = BASE_DIR / "static" / "plots"
ALLOWED_EXTENSIONS = {"csv", "txt"}

PVC_THRESHOLD = 0.6
TACHY_HR = 100
BRADY_HR = 50
PAUSE_SEC = 2.0
AF_CV_THRESHOLD = 0.15

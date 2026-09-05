from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

# Used only when a sampling rate cannot be inferred from the first CSV column.
FS = 500
UPLOAD_FOLDER = BASE_DIR / "uploads"
ANALYSIS_FOLDER = BASE_DIR / "analysis"
ALLOWED_EXTENSIONS = {"csv", "txt"}
TWELVE_LEAD_OVERVIEW_SECONDS = 10

# The analysis engine reads long recordings in blocks.  The values keep the
# working set bounded while still giving NeuroKit enough context at a block
# boundary.  They are deliberately expressed in samples only where a rate is
# not known before the first block is read.
ECG_CHUNK_ROWS = 150_000
# A short bilateral raw-signal buffer protects R-peak detection at a boundary.
ECG_PEAK_CONTEXT_SECONDS = 5.0
ECG_REVIEW_CONTEXT_SECONDS = 30.0
ECG_REVIEW_AMPLITUDE_LIMIT = 1.25
# Timestamps rounded to milliseconds may alternate by more than 5% at lower
# sample rates.  A missing sample creates a much larger jump and is rejected.
MAX_SAMPLING_JITTER_RATIO = 0.25

PVC_THRESHOLD = 0.6
TACHY_HR = 100
BRADY_HR = 50
PAUSE_SEC = 2.0
AF_CV_THRESHOLD = 0.15

# Conservative settings for the review-support algorithms below.  They are
# deliberately configuration, rather than hidden constants, so their values
# can be locked and validated for a defined intended use.
SIGNAL_QUALITY_MIN_SCORE = 0.45
QRS_CONSENSUS_TOLERANCE_SECONDS = 0.08
RHYTHM_WINDOW_SECONDS = 30.0
RHYTHM_WINDOW_STEP_SECONDS = 10.0

from io_utils import infer_sampling_rate, load_csv
from preprocessing import preprocess
from rpeaks import get_rpeaks
from features import rr_intervals

from arrhythmia.basic import detect_tachy_brady, detect_af
from arrhythmia.ventricular import detect_pvc, detect_bigeminy_trigeminy
from arrhythmia.rhythm import detect_pause
from arrhythmia.supraventricular import detect_pac, detect_sveb, detect_svt
from visualization import plot_ecg

from config import FS


def run(path, plot_path="static/plots/ecg_plot.png"):

    time, ecg = load_csv(path)
    sampling_rate = infer_sampling_rate(time, FS)

    cleaned = preprocess(ecg, sampling_rate)

    r_peaks = get_rpeaks(cleaned, sampling_rate)

    rr, hr = rr_intervals(r_peaks, sampling_rate)

    results = []

    # rhythm
    results += detect_tachy_brady(hr)
    results += detect_af(rr)

    # ventricular
    results += detect_pvc(rr)
    results += detect_bigeminy_trigeminy(rr)

    # supraventricular
    results += detect_pac(rr)
    results += detect_sveb(rr)
    results += detect_svt(hr, rr)

    # pauses
    results += detect_pause(rr)

    if plot_path:
        plot_ecg(time, cleaned, r_peaks, results, output_path=plot_path)

    return {
        "time": time,
        "ecg": cleaned,
        "r_peaks": r_peaks,
        "results": results,
        "rr": rr,
        "hr": hr,
        "sampling_rate": sampling_rate,
    }


if __name__ == "__main__":
    result = run("uploads/ecg.csv")

    print("=== DETECTED EVENTS ===")
    for r in result["results"]:
        print(r)

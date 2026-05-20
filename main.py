from io_utils import load_csv
from preprocessing import preprocess
from rpeaks import get_rpeaks
from features import rr_intervals

from arrhythmia.basic import detect_tachy_brady, detect_af
from arrhythmia.ventricular import detect_pvc, detect_bigeminy_trigeminy
from arrhythmia.rhythm import detect_pause
from visualization import plot_ecg
from arrhythmia.supraventricular import detect_pac, detect_sveb, detect_svt
from visualization import *
from config import FS


def run(path):
    time, ecg = load_csv(path)

    cleaned = preprocess(ecg, FS)
    r_peaks = get_rpeaks(cleaned, FS)
    
    rr, hr = rr_intervals(r_peaks, FS)

    results = []

    # rytm
    results += detect_tachy_brady(hr)
    results += detect_af(rr)

    # komorowe
    pvc = detect_pvc(rr)
    patterns = detect_bigeminy_trigeminy(rr)

    results += pvc
    results += patterns

    # nadkomorowe
    results += detect_pac(rr)
    results += detect_sveb(rr)
    results += detect_svt(hr, rr)

    # pauzy
    results += detect_pause(rr)

    # =========================
    # VISUALIZATION
    # =========================
    plot_ecg(
        time=time,
        ecg=cleaned,
        r_peaks=r_peaks,
        events=results
    )
    plot_rr(time=time,r_peaks=r_peaks)
    
    return {
        "r_peaks": r_peaks,
        "results": results,
        "rr": rr,
        "hr": hr
    }


if __name__ == "__main__":
    result = run("dane/holter_10min_500Hz_arrhythmia.csv")

    print("=== DETECTED EVENTS ===")
    for r in result["results"]:
        print(r)
from io_utils import infer_sampling_rate, load_ecg_csv
from leads import RHYTHM_ANALYSIS_LEAD, build_standard_12_leads
from preprocessing import preprocess
from rpeaks import get_rpeaks
from features import rr_intervals

from arrhythmia.basic import detect_tachy_brady, detect_af
from arrhythmia.ventricular import detect_pvc, detect_bigeminy_trigeminy
from arrhythmia.rhythm import detect_pause
from arrhythmia.supraventricular import detect_pac, detect_sveb, detect_svt
from visualization import plot_12_lead_ecg, plot_ecg

from config import FS, TWELVE_LEAD_OVERVIEW_SECONDS


def run(path, plot_path="static/plots/ecg_plot.png", twelve_lead_plot_path=None):

    time, recorded_leads, input_mode = load_ecg_csv(path)
    sampling_rate = infer_sampling_rate(time, FS)

    is_twelve_lead = input_mode == "ads1298_8_channel"
    if is_twelve_lead:
        leads = build_standard_12_leads(recorded_leads)
        analysis_lead = RHYTHM_ANALYSIS_LEAD
    else:
        leads = recorded_leads
        analysis_lead = next(iter(recorded_leads))

    ecg = leads[analysis_lead]

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
        plot_ecg(time, cleaned, r_peaks, results, output_path=plot_path, lead_name=analysis_lead)
    if is_twelve_lead and twelve_lead_plot_path:
        plot_12_lead_ecg(
            time,
            leads,
            output_path=twelve_lead_plot_path,
            overview_seconds=TWELVE_LEAD_OVERVIEW_SECONDS,
        )

    return {
        "time": time,
        "ecg": cleaned,
        "r_peaks": r_peaks,
        "results": results,
        "rr": rr,
        "hr": hr,
        "sampling_rate": sampling_rate,
        "is_twelve_lead": is_twelve_lead,
        "analysis_lead": analysis_lead,
        "recorded_leads": tuple(recorded_leads),
        "leads": leads,
    }


if __name__ == "__main__":
    result = run("uploads/ecg.csv")

    print("=== DETECTED EVENTS ===")
    for r in result["results"]:
        print(r)

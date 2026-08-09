"""Standard 12-lead ECG definitions and digital lead derivations.

The eight recorded ADS1298 channels are expected to be I, II, V1, V2, V3,
V4, V5 and V6. The remaining limb leads are mathematical derivations from
Leads I and II.
"""

from collections.abc import Mapping

import numpy as np


ADS1298_DIRECT_LEADS = ("I", "II", "V1", "V2", "V3", "V4", "V5", "V6")
STANDARD_12_LEAD_ORDER = ("I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6")
RHYTHM_ANALYSIS_LEAD = "II"


LEAD_DETAILS = (
    {
        "lead": "I",
        "source": "CH1 — LA -- RA (pomiar bezpośredni)",
        "view": "widok boczny wysoki",
    },
    {
        "lead": "II",
        "source": "CH2 — LL -- RA (pomiar bezpośredni)",
        "view": "widok dolny; podstawowe odprowadzenie do analizy rytmu",
    },
    {
        "lead": "III",
        "source": "II -- I = LL -- LA (wyliczane cyfrowo)",
        "view": "widok dolny",
    },
    {
        "lead": "aVR",
        "source": "--(I + II) / 2 (wyliczane cyfrowo)",
        "view": "widok z prawego barku / górny prawy",
    },
    {
        "lead": "aVL",
        "source": "I -- II / 2 (wyliczane cyfrowo)",
        "view": "widok boczny wysoki",
    },
    {
        "lead": "aVF",
        "source": "II -- I / 2 (wyliczane cyfrowo)",
        "view": "widok dolny",
    },
    {
        "lead": "V1",
        "source": "CH3 — elektroda V1 -- WCT (pomiar bezpośredni)",
        "view": "przegroda / prawa część serca",
    },
    {
        "lead": "V2",
        "source": "CH4 — elektroda V2 -- WCT (pomiar bezpośredni)",
        "view": "przegroda",
    },
    {
        "lead": "V3",
        "source": "CH5 — elektroda V3 -- WCT (pomiar bezpośredni)",
        "view": "ściana przednia",
    },
    {
        "lead": "V4",
        "source": "CH6 — elektroda V4 -- WCT (pomiar bezpośredni)",
        "view": "ściana przednia / koniuszek",
    },
    {
        "lead": "V5",
        "source": "CH7 — elektroda V5 -- WCT (pomiar bezpośredni)",
        "view": "ściana boczna",
    },
    {
        "lead": "V6",
        "source": "CH8 — elektroda V6 -- WCT (pomiar bezpośredni)",
        "view": "ściana boczna",
    },
)


def build_standard_12_leads(recorded_leads: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Return all 12 standard leads from the eight ADS1298 direct recordings.

    The formulae implement Einthoven's law and Goldberger augmented leads:
    III = II - I, aVR = -(I + II)/2, aVL = I - II/2, aVF = II - I/2.
    """
    missing = [lead for lead in ADS1298_DIRECT_LEADS if lead not in recorded_leads]
    if missing:
        raise ValueError(f"Brak wymaganych kanałów ADS1298: {', '.join(missing)}.")

    direct = {lead: np.asarray(recorded_leads[lead], dtype=float) for lead in ADS1298_DIRECT_LEADS}
    sample_count = len(direct["I"])
    if sample_count < 3 or any(values.ndim != 1 or len(values) != sample_count for values in direct.values()):
        raise ValueError("Wszystkie kanały ADS1298 muszą mieć tę samą, niezerową liczbę próbek.")

    lead_i = direct["I"]
    lead_ii = direct["II"]

    return {
        "I": lead_i,
        "II": lead_ii,
        "III": lead_ii - lead_i,
        "aVR": -(lead_i + lead_ii) / 2,
        "aVL": lead_i - lead_ii / 2,
        "aVF": lead_ii - lead_i / 2,
        "V1": direct["V1"],
        "V2": direct["V2"],
        "V3": direct["V3"],
        "V4": direct["V4"],
        "V5": direct["V5"],
        "V6": direct["V6"],
    }

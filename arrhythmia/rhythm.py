import numpy as np
from config import PAUSE_SEC

def detect_pause(rr):
    events = []

    for i, r in enumerate(rr):
        if r > PAUSE_SEC:
            events.append(("Pause", i))

    return events
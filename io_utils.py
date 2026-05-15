import numpy as np
import pandas as pd

def load_csv(path):
    data = pd.read_csv(path, header=None, sep=';')  # 👈 TO JEST KLUCZ

    time = data.iloc[:, 0].values
    voltage = data.iloc[:, 1].values

    return time, voltage
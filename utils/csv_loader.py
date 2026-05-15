import pandas as pd

def load_ecg_csv(path):

    df = pd.read_csv(
        path,
        header=None,
        sep=';'
    )

    time = df.iloc[:, 0].astype(float).values
    voltage = df.iloc[:, 1].astype(float).values

    return time, voltage
import pandas as pd


def load_dataset(path: str):
    df = pd.read_csv(path, sep=None, engine='python')
    detected_cols = [column.strip().lower() for column in df.columns]
    return df, detected_cols

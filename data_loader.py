# data_loader.py
import pandas as pd
import numpy as np

def simulate_neonatal_vitals(duration_seconds=300, include_anomaly=True):
    """
    Simulate realistic neonatal vital signs stream.
    Based on WHO neonatal normal ranges.
    """
    np.random.seed(42)
    t = np.arange(duration_seconds)

    # Normal ranges per WHO neonatal standards
    HR  = 140 + 10 * np.sin(0.05 * t) + np.random.normal(0, 3, duration_seconds)
    SpO2 = 97 + np.random.normal(0, 0.5, duration_seconds)
    RR   = 45 + 5 * np.sin(0.03 * t) + np.random.normal(0, 2, duration_seconds)
    Temp = 36.8 + np.random.normal(0, 0.1, duration_seconds)

    if include_anomaly:
        # Inject real anomaly at t=200 (apnea + bradycardia)
        SpO2[200:220] = np.linspace(97, 72, 20)   # SpO2 drops
        HR[205:220]   = np.linspace(140, 85, 15)  # Heart rate drops
        RR[200:215]   = np.linspace(45, 10, 15)   # Breathing slows

    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=duration_seconds, freq='1s'),
        'HR': HR, 'SpO2': SpO2, 'RR': RR, 'Temp': Temp
    })
    return df

# Load real data (HuggingFace dataset)
from datasets import load_dataset

def load_neonatal_dataset():
    dataset = load_dataset(
        "electricsheepafrica/neonatal-birth-outcomes",
        "moderate_burden"
    )
    return dataset["train"].to_pandas()
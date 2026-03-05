# anomaly_detector.py
import torch
import numpy as np
import pandas as pd
from chronos import BaseChronosPipeline

# Load Chronos-Bolt (250x faster than original Chronos)
pipeline = BaseChronosPipeline.from_pretrained(
    "amazon/chronos-bolt-small",   # Use 'base' for better accuracy
    device_map="cpu",              # Use "cuda" if GPU available
    torch_dtype=torch.float32,
)

def detect_anomaly(vital_series: np.ndarray, 
                   vital_name: str,
                   context_length: int = 60,
                   forecast_steps: int = 10):

    context = torch.tensor(vital_series[-context_length:], 
                          dtype=torch.float32).unsqueeze(0)
    
    forecast = pipeline.predict(
        context,
        prediction_length=forecast_steps,
    )
    
    # Convert to plain Python floats — fixes the ambiguous array comparison
    forecast_np = forecast[0].numpy().flatten()
    
    low  = (forecast_np * 0.90).tolist()
    mid  = forecast_np.tolist()
    high = (forecast_np * 1.10).tolist()
    
    actual = vital_series[-forecast_steps:].tolist()
    
    # Now comparing plain Python floats — no more ambiguity
    deviation_scores = []
    for i, val in enumerate(actual):
        val = float(val)
        if val < low[i]:
            dev = (low[i] - val) / (high[i] - low[i] + 1e-6)
        elif val > high[i]:
            dev = (val - high[i]) / (high[i] - low[i] + 1e-6)
        else:
            dev = 0.0
        deviation_scores.append(dev)
    
    max_deviation = max(deviation_scores)
    
    return {
        'vital': vital_name,
        'actual': actual,
        'predicted_low': low,
        'predicted_mid': mid,
        'predicted_high': high,
        'deviation_score': round(max_deviation, 3),
        'is_anomalous': max_deviation > 0.5
    }
def analyze_all_vitals(df):
    results = {}
    for vital in ['HR', 'SpO2', 'RR', 'Temp']:
        series = df[vital].values.astype(float)
        results[vital] = detect_anomaly(series, vital)
    return results
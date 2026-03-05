# signal_filter.py
import neurokit2 as nk
import numpy as np

def compute_signal_quality(signal, signal_type='HR'):
    """
    Returns quality score 0-1.
    Below 0.6 = likely motion artifact → skip this reading
    """
    try:
        if signal_type == 'SpO2':
            # Check for physiologically impossible rapid changes
            diff = np.abs(np.diff(signal))
            if np.any(diff > 10):  # >10% drop per second = artifact
                return 0.2
        
        # Check for flat line (sensor disconnect)
        if np.std(signal) < 0.01:
            return 0.1
            
        # Check for out-of-range values
        normal_ranges = {
            'HR':   (60, 220),
            'SpO2': (50, 100),
            'RR':   (10, 100),
            'Temp': (34.0, 41.0)
        }
        lo, hi = normal_ranges.get(signal_type, (0, 9999))
        out_of_range = np.mean((signal < lo) | (signal > hi))
        
        if out_of_range > 0.3:
            return 0.3
            
        return 1.0  # Good quality signal
        
    except:
        return 0.5

def filter_vitals(df, window=30):
    """Filter a rolling window of vitals for quality."""
    quality_scores = {}
    for col in ['HR', 'SpO2', 'RR', 'Temp']:
        recent = df[col].tail(window).values
        quality_scores[col] = compute_signal_quality(recent, col)
    
    # Overall quality — if any critical vital is bad, flag it
    overall = min(quality_scores['HR'], quality_scores['SpO2'])
    return overall, quality_scores
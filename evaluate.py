# evaluate.py
from sklearn.metrics import precision_score, recall_score, f1_score
import numpy as np

def evaluate_system(predictions, ground_truth):
    """
    Ground truth: 1 = real anomaly, 0 = false alarm
    Predictions:  1 = our system flagged HIGH, 0 = not flagged
    """
    precision = precision_score(ground_truth, predictions)
    recall    = recall_score(ground_truth, predictions)
    f1        = f1_score(ground_truth, predictions)
    
    # False alarm rate (most important metric for alarm fatigue)
    false_alarms    = sum((p==1 and g==0) for p,g in zip(predictions, ground_truth))
    total_alarms    = sum(predictions)
    false_alarm_rate = false_alarms / total_alarms if total_alarms > 0 else 0
    
    print(f"Precision:       {precision:.2%}")
    print(f"Recall:          {recall:.2%}")
    print(f"F1 Score:        {f1:.2%}")
    print(f"False Alarm Rate:{false_alarm_rate:.2%}")
    print(f"(Industry avg false alarm rate: 87.5%)")
    
    return {'precision': precision, 'recall': recall,
            'f1': f1, 'false_alarm_rate': false_alarm_rate}
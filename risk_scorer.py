# risk_scorer.py

# Gestational age-specific thresholds (WHO standards)
THRESHOLDS = {
    'extremely_preterm': {  # < 28 weeks
        'HR':   (100, 180), 'SpO2': (88, 100),
        'RR':   (40, 70),   'Temp': (36.0, 37.5)
    },
    'very_preterm': {       # 28–32 weeks
        'HR':   (110, 170), 'SpO2': (90, 100),
        'RR':   (40, 65),   'Temp': (36.2, 37.5)
    },
    'late_preterm': {       # 32–36 weeks
        'HR':   (120, 160), 'SpO2': (92, 100),
        'RR':   (40, 60),   'Temp': (36.5, 37.5)
    },
    'term': {               # > 36 weeks
        'HR':   (120, 160), 'SpO2': (95, 100),
        'RR':   (30, 60),   'Temp': (36.5, 37.5)
    }
}

def compute_risk_score(anomaly_results: dict,
                       gestational_age_weeks: float,
                       signal_quality: float) -> dict:
    """
    Combines anomaly scores into a final risk level.
    Only HIGH risk triggers an alert — eliminates alarm fatigue.
    """
    
    # Determine gestational age category
    if gestational_age_weeks < 28:
        ga_category = 'extremely_preterm'
    elif gestational_age_weeks < 32:
        ga_category = 'very_preterm'
    elif gestational_age_weeks < 37:
        ga_category = 'late_preterm'
    else:
        ga_category = 'term'
    
    # Weight by clinical importance
    weights = {'SpO2': 0.40, 'HR': 0.35, 'RR': 0.20, 'Temp': 0.05}
    
    composite_score = 0
    contributing_vitals = []
    
    for vital, result in anomaly_results.items():
        if result['is_anomalous']:
            weighted = result['deviation_score'] * weights[vital]
            composite_score += weighted
            contributing_vitals.append({
                'vital': vital,
                'deviation': result['deviation_score'],
                'actual_value': result['actual'][-1]
            })
    
    # Signal quality penalty — poor signal reduces confidence
    confidence = signal_quality
    
    # Risk classification
    if composite_score >= 0.6 and confidence > 0.7:
        risk_level = "HIGH"       # 🔴 Alert fires
    elif composite_score >= 0.3:
        risk_level = "MEDIUM"     # 🟡 Log only
    else:
        risk_level = "LOW"        # 🟢 Normal — no alert
    
    return {
        'risk_level': risk_level,
        'composite_score': round(composite_score, 3),
        'confidence': round(confidence, 2),
        'ga_category': ga_category,
        'contributing_vitals': contributing_vitals,
        'alert': risk_level == "HIGH"
    }
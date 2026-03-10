import numpy as np
from collections import deque
import time

# ─────────────────────────────────────────────────────────────
# SECTION 1: CORRECTED GESTATIONAL AGE ENGINE
# Key insight: A 25-week baby in NICU for 60 days has a
# corrected GA of 25 + (60/7) = 33.6 weeks — thresholds
# must reflect this maturation, not just birth GA.
# ─────────────────────────────────────────────────────────────

def get_corrected_gestational_age(ga_at_birth: float, days_in_nicu: int) -> float:
    """
    Corrected GA = GA at birth + weeks alive in NICU.
    This is the TRUE clinical age used for threshold selection.
    """
    weeks_alive = days_in_nicu / 7
    return ga_at_birth + weeks_alive


def get_monitoring_phase(corrected_ga: float) -> str:
    """
    Phase determines HOW aggressively the system monitors.
    Based on corrected gestational age milestones.
    """
    if corrected_ga < 32:
        return 'acute'           # Max monitoring — highest risk
    elif corrected_ga < 36:
        return 'extended'        # Moderate monitoring
    elif corrected_ga < 40:
        return 'step_down'       # Apnea + temp focus only
    else:
        return 'discharge_ready' # Final safety checks


def get_ga_category(corrected_ga: float) -> str:
    """GA category based on CORRECTED GA — not birth GA."""
    if corrected_ga < 28:   return 'extremely_preterm'
    elif corrected_ga < 32: return 'very_preterm'
    elif corrected_ga < 37: return 'late_preterm'
    else:                   return 'term'


# ─────────────────────────────────────────────────────────────
# SECTION 2: CLINICALLY VALIDATED THRESHOLDS
# Sources:
#   - Fleming et al. Lancet 2011 (HR, RR)
#   - SUPPORT/BOOST-II/COT trials (SpO2 targets)
#   - Philadelphia Neonatal BP Study (BP by GA)
#   - WHO Neonatal Care Guidelines 2023
# ─────────────────────────────────────────────────────────────

NEONATAL_THRESHOLDS = {
    'extremely_preterm': {   # Corrected GA < 28 weeks
        'HR':   {'min': 100, 'max': 180, 'critical_low': 80,   'critical_high': 205},
        'SpO2': {'min': 90,  'max': 95,  'critical_low': 80,   'critical_high': 98},
        'RR':   {'min': 40,  'max': 70,  'critical_low': 20,   'critical_high': 90},
        'Temp': {'min': 36.0,'max': 37.5,'critical_low': 35.5, 'critical_high': 38.0},
        'SBP':  {'min': 35,  'max': 55,  'critical_low': 25,   'critical_high': 70},
        'DBP':  {'min': 15,  'max': 35,  'critical_low': 10,   'critical_high': 45},
        'MAP':  {'min': 27,  'max': 45,  'critical_low': 20,   'critical_high': 55},
    },
    'very_preterm': {        # Corrected GA 28–31 weeks
        'HR':   {'min': 110, 'max': 170, 'critical_low': 90,   'critical_high': 195},
        'SpO2': {'min': 91,  'max': 95,  'critical_low': 82,   'critical_high': 98},
        'RR':   {'min': 40,  'max': 65,  'critical_low': 25,   'critical_high': 85},
        'Temp': {'min': 36.2,'max': 37.5,'critical_low': 35.5, 'critical_high': 38.0},
        'SBP':  {'min': 40,  'max': 60,  'critical_low': 30,   'critical_high': 75},
        'DBP':  {'min': 20,  'max': 40,  'critical_low': 12,   'critical_high': 50},
        'MAP':  {'min': 35,  'max': 50,  'critical_low': 25,   'critical_high': 60},
    },
    'late_preterm': {        # Corrected GA 32–36 weeks
        'HR':   {'min': 120, 'max': 160, 'critical_low': 95,   'critical_high': 190},
        'SpO2': {'min': 92,  'max': 97,  'critical_low': 85,   'critical_high': 99},
        'RR':   {'min': 40,  'max': 60,  'critical_low': 25,   'critical_high': 80},
        'Temp': {'min': 36.4,'max': 37.5,'critical_low': 36.0, 'critical_high': 38.0},
        'SBP':  {'min': 45,  'max': 65,  'critical_low': 35,   'critical_high': 80},
        'DBP':  {'min': 25,  'max': 45,  'critical_low': 15,   'critical_high': 55},
        'MAP':  {'min': 40,  'max': 55,  'critical_low': 28,   'critical_high': 65},
    },
    'term': {                # Corrected GA >= 37 weeks
        'HR':   {'min': 120, 'max': 160, 'critical_low': 100,  'critical_high': 180},
        'SpO2': {'min': 95,  'max': 100, 'critical_low': 88,   'critical_high': 100},
        'RR':   {'min': 30,  'max': 60,  'critical_low': 20,   'critical_high': 75},
        'Temp': {'min': 36.5,'max': 37.5,'critical_low': 36.0, 'critical_high': 38.5},
        'SBP':  {'min': 55,  'max': 75,  'critical_low': 40,   'critical_high': 90},
        'DBP':  {'min': 30,  'max': 50,  'critical_low': 20,   'critical_high': 65},
        'MAP':  {'min': 45,  'max': 60,  'critical_low': 30,   'critical_high': 70},
    },
}

# Phase-based monitoring — step_down and discharge_ready
# only watch the most critical vitals
PHASE_WATCHED_VITALS = {
    'acute':            ['HR', 'SpO2', 'RR', 'Temp', 'SBP', 'DBP', 'MAP'],
    'extended':         ['HR', 'SpO2', 'RR', 'Temp', 'MAP'],
    'step_down':        ['SpO2', 'HR', 'RR', 'Temp'],
    'discharge_ready':  ['SpO2', 'HR', 'Temp'],
}

# ─────────────────────────────────────────────────────────────
# SECTION 3: CLINICAL CONDITION PATTERNS
# Multi-vital AND logic — all conditions must be true
# simultaneously before an alert fires.
# Persistence duration prevents transient false alarms.
# ─────────────────────────────────────────────────────────────

CLINICAL_PATTERNS = {

    # ── RESPIRATORY ──────────────────────────────────────────
    'apnea_bradycardia_desaturation': {
        'label': 'ABD Event',
        'phases': ['acute', 'extended', 'step_down'],
        'required_vitals': ['SpO2', 'HR', 'RR'],
        'conditions': {
            'SpO2': lambda v, t: v < t['SpO2']['min'],
            'HR':   lambda v, t: v < t['HR']['min'],
            'RR':   lambda v, t: v < t['RR']['min'],
        },
        'severity': 'CRITICAL',
        'min_duration_seconds': 15,
        'description': 'Apnea with Bradycardia and Desaturation (ABD event)',
        'action': 'Stimulate infant immediately. Prepare bag-mask ventilation. Call physician.',
    },
    'isolated_apnea': {
        'label': 'Apnea',
        'phases': ['acute', 'extended', 'step_down', 'discharge_ready'],
        'required_vitals': ['RR'],
        'conditions': {
            'RR': lambda v, t: v < t['RR']['critical_low'],
        },
        'severity': 'HIGH',
        'min_duration_seconds': 20,
        'description': 'Apneic episode — respiratory pause detected',
        'action': 'Stimulate infant. Monitor for bradycardia development.',
    },
    'respiratory_distress': {
        'label': 'RDS',
        'phases': ['acute', 'extended'],
        'required_vitals': ['RR', 'SpO2'],
        'conditions': {
            'RR':   lambda v, t: v > t['RR']['max'],
            'SpO2': lambda v, t: v < t['SpO2']['min'],
        },
        'severity': 'HIGH',
        'min_duration_seconds': 30,
        'description': 'Respiratory distress — tachypnea with hypoxemia',
        'action': 'Increase respiratory support. Consider CPAP. Call respiratory team.',
    },
    'hypoxemia_critical': {
        'label': 'Hypoxemia',
        'phases': ['acute', 'extended', 'step_down', 'discharge_ready'],
        'required_vitals': ['SpO2'],
        'conditions': {
            'SpO2': lambda v, t: v < t['SpO2']['critical_low'],
        },
        'severity': 'CRITICAL',
        'min_duration_seconds': 10,
        'description': 'Critical hypoxemia — SpO2 below safe threshold',
        'action': 'Increase FiO2. Check airway. Call physician immediately.',
    },

    # ── CARDIOVASCULAR ────────────────────────────────────────
    'bradycardia_isolated': {
        'label': 'Bradycardia',
        'phases': ['acute', 'extended', 'step_down'],
        'required_vitals': ['HR'],
        'conditions': {
            'HR': lambda v, t: v < t['HR']['critical_low'],
        },
        'severity': 'CRITICAL',
        'min_duration_seconds': 10,
        'description': 'Critical bradycardia — heart rate dangerously low',
        'action': 'Stimulate infant. Check airway. Prepare resuscitation.',
    },
    'tachycardia_isolated': {
        'label': 'Tachycardia',
        'phases': ['acute', 'extended'],
        'required_vitals': ['HR'],
        'conditions': {
            'HR': lambda v, t: v > t['HR']['critical_high'],
        },
        'severity': 'HIGH',
        'min_duration_seconds': 30,
        'description': 'Sustained tachycardia — possible pain, fever, or SVT',
        'action': 'Assess for pain, fever, or arrhythmia. Notify physician.',
    },
    'hypotension_shock': {
        'label': 'Hypotension',
        'phases': ['acute', 'extended'],
        'required_vitals': ['MAP', 'HR'],
        'conditions': {
            'MAP': lambda v, t: v < t['MAP']['critical_low'],
            'HR':  lambda v, t: v > t['HR']['max'],
        },
        'severity': 'CRITICAL',
        'min_duration_seconds': 20,
        'description': 'Hypotension with compensatory tachycardia — possible shock',
        'action': 'IV fluid bolus 10ml/kg. Notify physician. Prepare vasopressors.',
    },
    'hypertension_sustained': {
        'label': 'Hypertension',
        'phases': ['acute', 'extended', 'step_down'],
        'required_vitals': ['SBP'],
        'conditions': {
            'SBP': lambda v, t: v > t['SBP']['critical_high'],
        },
        'severity': 'HIGH',
        'min_duration_seconds': 120,
        'description': 'Sustained hypertension — SBP above 95th percentile',
        'action': 'Notify physician. Consider antihypertensive evaluation.',
    },

    # ── INFECTION / SEPSIS ────────────────────────────────────
    'early_sepsis': {
        'label': 'Sepsis',
        'phases': ['acute', 'extended'],
        'required_vitals': ['HR', 'Temp', 'RR'],
        'conditions': {
            'HR':   lambda v, t: v > t['HR']['max'],
            'Temp': lambda v, t: v > t['Temp']['max'],
            'RR':   lambda v, t: v > t['RR']['max'],
        },
        'severity': 'HIGH',
        'min_duration_seconds': 60,
        'description': 'Early sepsis signature — tachycardia, fever, tachypnea',
        'action': 'Draw blood cultures immediately. Start sepsis workup. Notify physician.',
    },
    'cold_sepsis': {
        'label': 'Cold Sepsis',
        'phases': ['acute', 'extended'],
        'required_vitals': ['HR', 'Temp'],
        'conditions': {
            'HR':   lambda v, t: v > t['HR']['max'],
            'Temp': lambda v, t: v < t['Temp']['min'],
        },
        'severity': 'HIGH',
        'min_duration_seconds': 45,
        'description': 'Cold sepsis pattern — tachycardia with hypothermia',
        'action': 'Urgent sepsis workup. Warming measures. Notify physician.',
    },

    # ── TEMPERATURE ───────────────────────────────────────────
    'hypothermia': {
        'label': 'Hypothermia',
        'phases': ['acute', 'extended', 'step_down'],
        'required_vitals': ['Temp', 'HR'],
        'conditions': {
            'Temp': lambda v, t: v < t['Temp']['min'],
            'HR':   lambda v, t: v < t['HR']['min'],
        },
        'severity': 'HIGH',
        'min_duration_seconds': 30,
        'description': 'Hypothermia with bradycardia — cold stress detected',
        'action': 'Increase incubator temperature. Apply warming. Check glucose.',
    },
    'hyperthermia': {
        'label': 'Hyperthermia',
        'phases': ['acute', 'extended', 'step_down'],
        'required_vitals': ['Temp'],
        'conditions': {
            'Temp': lambda v, t: v > t['Temp']['critical_high'],
        },
        'severity': 'HIGH',
        'min_duration_seconds': 60,
        'description': 'Hyperthermia — possible infection or overheating',
        'action': 'Reduce incubator temp. Blood culture if infection suspected.',
    },

    # ── DISCHARGE READINESS ───────────────────────────────────
    'apnea_near_discharge': {
        'label': 'Pre-discharge Apnea',
        'phases': ['discharge_ready'],
        'required_vitals': ['SpO2', 'HR'],
        'conditions': {
            'SpO2': lambda v, t: v < t['SpO2']['min'],
            'HR':   lambda v, t: v < t['HR']['min'],
        },
        'severity': 'CRITICAL',
        'min_duration_seconds': 10,
        'description': 'Apnea event near discharge — delays discharge criteria',
        'action': 'Reset apnea-free clock. Notify physician. Delay discharge.',
    },
}

# ─────────────────────────────────────────────────────────────
# SECTION 4: PERSISTENCE TRACKER
# Mathematical core of alarm fatigue prevention.
# Vital must be outside range for N consecutive seconds.
# ─────────────────────────────────────────────────────────────

class PersistenceTracker:
    def __init__(self, window_seconds=180):
        self.window = window_seconds
        self.history = {
            'HR': deque(), 'SpO2': deque(), 'RR': deque(),
            'Temp': deque(), 'SBP': deque(), 'DBP': deque(), 'MAP': deque()
        }
        self.last_alert_time = {}
        self.ALERT_COOLDOWN = 120   # 2 minutes between same alert

    def update(self, vitals: dict, timestamp: float = None):
        if timestamp is None:
            timestamp = time.time()
        for vital, value in vitals.items():
            if vital in self.history:
                self.history[vital].append((timestamp, float(value)))
                while (self.history[vital] and
                       timestamp - self.history[vital][0][0] > self.window):
                    self.history[vital].popleft()

    def get_consecutive_abnormal_seconds(self, vital: str,
                                          thresh: dict,
                                          value: float) -> float:
        """
        Walks BACKWARDS through history.
        Returns consecutive seconds the vital has been abnormal.
        Resets to 0 the moment it was normal.
        """
        readings = list(self.history[vital])
        if len(readings) < 2:
            return 0.0

        t_low  = thresh[vital]['min']
        t_high = thresh[vital]['max']

        consecutive = 0.0
        for i in range(len(readings) - 1, 0, -1):
            ts, val = readings[i]
            prev_ts = readings[i - 1][0]
            interval = ts - prev_ts
            is_abnormal = (val < t_low) or (val > t_high)
            if is_abnormal:
                consecutive += interval
            else:
                break   # Chain broken — stop counting
        return consecutive

    def can_alert(self, condition_name: str) -> bool:
        now = time.time()
        last = self.last_alert_time.get(condition_name, 0)
        return (now - last) > self.ALERT_COOLDOWN

    def record_alert(self, condition_name: str):
        self.last_alert_time[condition_name] = time.time()


# ─────────────────────────────────────────────────────────────
# SECTION 5: SEVERITY SCORING
# Z-score style: how far is value from normal range?
# 0 = normal, 1 = at boundary, >1 = critically outside
# ─────────────────────────────────────────────────────────────

def compute_severity_score(vital: str, value: float, thresh: dict) -> float:
    t = thresh[vital]
    range_width = max(t['max'] - t['min'], 1e-6)
    if value < t['min']:
        return round((t['min'] - value) / range_width, 3)
    elif value > t['max']:
        return round((value - t['max']) / range_width, 3)
    return 0.0


# ─────────────────────────────────────────────────────────────
# SECTION 6: MAIN PATTERN DETECTOR
# ─────────────────────────────────────────────────────────────

def detect_clinical_patterns(current_vitals: dict,
                              tracker: PersistenceTracker,
                              ga_at_birth: float,
                              days_in_nicu: int = 0) -> list:
    corrected_ga  = get_corrected_gestational_age(ga_at_birth, days_in_nicu)
    ga_category   = get_ga_category(corrected_ga)
    phase         = get_monitoring_phase(corrected_ga)
    thresh        = NEONATAL_THRESHOLDS[ga_category]
    watched       = PHASE_WATCHED_VITALS[phase]
    alerts        = []

    for condition_name, pattern in CLINICAL_PATTERNS.items():

        # Only run patterns relevant to current monitoring phase
        if phase not in pattern['phases']:
            continue

        required = pattern['required_vitals']

        # Only use vitals that are being watched in this phase
        if not all(v in watched for v in required):
            continue

        # All required vitals must be present in current reading
        if not all(v in current_vitals for v in required):
            continue

        # ALL conditions must be true simultaneously (AND logic)
        all_met = all(
            pattern['conditions'][v](current_vitals[v], thresh)
            for v in required
        )
        if not all_met:
            continue

        # Persistence check — must be abnormal for minimum duration
        durations = [
            tracker.get_consecutive_abnormal_seconds(
                v, thresh, current_vitals[v]
            )
            for v in required
        ]
        min_duration_observed = min(durations)

        if min_duration_observed < pattern['min_duration_seconds']:
            continue   # Too brief — artifact or transient change

        # Cooldown check — don't repeat same alert within 2 min
        if not tracker.can_alert(condition_name):
            continue

        # Severity scoring
        scores = {
            v: compute_severity_score(v, current_vitals[v], thresh)
            for v in required
        }
        composite = round(sum(scores.values()) / len(scores), 3)

        alerts.append({
            'condition':   condition_name,
            'label':       pattern['label'],
            'severity':    pattern['severity'],
            'description': pattern['description'],
            'action':      pattern['action'],
            'duration_seconds': round(min_duration_observed, 1),
            'composite_score':  composite,
            'corrected_ga':     round(corrected_ga, 1),
            'phase':            phase,
            'ga_category':      ga_category,
            'contributing_vitals': [
                {
                    'vital':       v,
                    'actual_value': round(current_vitals[v], 1),
                    'normal_min':  thresh[v]['min'],
                    'normal_max':  thresh[v]['max'],
                    'deviation':   scores.get(v, 0),
                }
                for v in required
            ],
        })

        tracker.record_alert(condition_name)

    # CRITICAL first, then HIGH
    severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2}
    alerts.sort(key=lambda x: severity_order.get(x['severity'], 3))
    return alerts


# ─────────────────────────────────────────────────────────────
# SECTION 7: SYNTHETIC VITAL GENERATOR
# Simulates realistic incubator sensor output per scenario.
# MAP = (SBP + 2*DBP) / 3 — standard clinical formula.
# ─────────────────────────────────────────────────────────────

def generate_synthetic_vitals(t: int,
                               ga_at_birth: float,
                               days_in_nicu: int = 0,
                               scenario: str = 'normal') -> dict:
    corrected_ga = get_corrected_gestational_age(ga_at_birth, days_in_nicu)
    ga_cat       = get_ga_category(corrected_ga)
    thresh       = NEONATAL_THRESHOLDS[ga_cat]
    rng          = np.random.default_rng(seed=(t * 7 + int(ga_at_birth * 3)) % 99991)

    # Baseline = midpoint of normal range
    HR   = (thresh['HR']['min']   + thresh['HR']['max'])   / 2
    SpO2 = (thresh['SpO2']['min'] + thresh['SpO2']['max']) / 2
    RR   = (thresh['RR']['min']   + thresh['RR']['max'])   / 2
    Temp = (thresh['Temp']['min'] + thresh['Temp']['max']) / 2
    SBP  = (thresh['SBP']['min']  + thresh['SBP']['max'])  / 2
    DBP  = (thresh['DBP']['min']  + thresh['DBP']['max'])  / 2

    # Physiological noise (small natural variation)
    HR   += rng.normal(0, 2.5)
    SpO2 += rng.normal(0, 0.4)
    RR   += rng.normal(0, 1.5)
    Temp += rng.normal(0, 0.06)
    SBP  += rng.normal(0, 1.8)
    DBP  += rng.normal(0, 1.3)

    # ── SCENARIO INJECTION ──────────────────────────────────
    # Progressive onset — not sudden — to mimic real physiology

    if scenario == 'apnea' and t > 30:
        p = min((t - 30) / 20.0, 1.0)
        SpO2 -= p * 18
        HR   -= p * 40
        RR   -= p * 28

    elif scenario == 'sepsis' and t > 20:
        p = min((t - 20) / 40.0, 1.0)
        HR   += p * 32
        Temp += p * 1.6
        RR   += p * 22

    elif scenario == 'hypothermia' and t > 15:
        p = min((t - 15) / 30.0, 1.0)
        Temp -= p * 1.8
        HR   -= p * 28

    elif scenario == 'hypoxemia' and t > 10:
        p = min((t - 10) / 15.0, 1.0)
        SpO2 -= p * 24

    elif scenario == 'hypotension' and t > 25:
        p = min((t - 25) / 20.0, 1.0)
        SBP  -= p * 22
        DBP  -= p * 16
        HR   += p * 28

    elif scenario == 'cold_sepsis' and t > 20:
        p = min((t - 20) / 35.0, 1.0)
        HR   += p * 30
        Temp -= p * 1.2

    elif scenario == 'hypertension' and t > 30:
        p = min((t - 30) / 60.0, 1.0)
        SBP  += p * 28
        DBP  += p * 18

    # MAP = standard clinical formula: (SBP + 2*DBP) / 3
    MAP = (SBP + 2 * DBP) / 3

    # Clip to physiologically possible ranges
    vitals = {
        'HR':   float(np.clip(HR,   40,  250)),
        'SpO2': float(np.clip(SpO2, 50,  100)),
        'RR':   float(np.clip(RR,   5,   120)),
        'Temp': float(np.clip(Temp, 33,  42)),
        'SBP':  float(np.clip(SBP,  20,  130)),
        'DBP':  float(np.clip(DBP,  10,  90)),
        'MAP':  float(np.clip(MAP,  15,  100)),
    }
    return {k: round(v, 1) for k, v in vitals.items()}
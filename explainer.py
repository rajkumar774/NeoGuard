import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

CONDITION_PATTERNS = {
    'apnea':        {'SpO2': 'low', 'HR': 'low', 'RR': 'low'},
    'bradycardia':  {'HR': 'low'},
    'tachycardia':  {'HR': 'high'},
    'sepsis_early': {'HR': 'high', 'Temp': 'high', 'RR': 'high'},
    'hypothermia':  {'Temp': 'low', 'HR': 'low'},
    'RDS':          {'SpO2': 'low', 'RR': 'high'},
}

def identify_pattern(contributing_vitals: list) -> str:
    vital_directions = {}
    for v in contributing_vitals:
        vital_directions[v['vital']] = 'low' if v['deviation'] < 0 else 'high'
    for condition, pattern in CONDITION_PATTERNS.items():
        if all(vital_directions.get(k) == v for k, v in pattern.items()):
            return condition
    return "unknown pattern"

def generate_explanation(risk_result, anomaly_results, gestational_age):
    vitals_summary = []
    for v in risk_result['contributing_vitals']:
        vital_name = v['vital']
        actual = round(v['actual_value'], 1)
        pred_mid = round(anomaly_results[vital_name]['predicted_mid'][-1], 1)
        vitals_summary.append(f"{vital_name}: actual={actual}, expected={pred_mid}")

    pattern = identify_pattern(risk_result['contributing_vitals'])

    prompt = f"""You are a neonatal clinical decision support AI.

Patient: {gestational_age}-week gestational age neonate
Risk Level: {risk_result['risk_level']}
Anomaly Score: {risk_result['composite_score']}
Detected Pattern: {pattern}
Abnormal Vitals: {'; '.join(vitals_summary)}

Generate a 2-sentence clinical alert explanation for the bedside nurse.
Be specific, concise, and clinical. State what is abnormal and what it may indicate.
Do NOT use technical jargon. Output only the explanation, nothing else."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
    )

    return response.choices[0].message.content


def get_suggested_action(risk_result):
    actions = {
        'apnea':        'Stimulate infant immediately. Prepare CPAP.',
        'bradycardia':  'Check airway. Prepare for resuscitation.',
        'sepsis_early': 'Draw blood cultures. Notify physician.',
        'hypothermia':  'Apply warming measures immediately.',
        'RDS':          'Increase O2 support. Notify respiratory team.',
    }
    pattern = identify_pattern(risk_result.get('contributing_vitals', []))
    return actions.get(pattern, 'Visually assess infant and notify physician.')


def explain_alert(risk_result, anomaly_results, gestational_age):
    explanation = generate_explanation(risk_result, anomaly_results, gestational_age)

    feature_importance = sorted(
        risk_result['contributing_vitals'],
        key=lambda x: x['deviation'],
        reverse=True
    )

    return {
        'explanation': explanation,
        'primary_cause': feature_importance[0]['vital'] if feature_importance else 'Unknown',
        'feature_importance': feature_importance,
        'suggested_action': get_suggested_action(risk_result)
    }
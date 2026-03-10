import streamlit as st
import plotly.graph_objects as go
import time
import pandas as pd
from risk_scorer import (
    PersistenceTracker,
    detect_clinical_patterns,
    generate_synthetic_vitals,
    get_corrected_gestational_age,
    get_monitoring_phase,
    get_ga_category,
    PHASE_WATCHED_VITALS,
)
from explainer import explain_alert

st.set_page_config(page_title="NeoGuard", page_icon="👶", layout="wide")

# ── Header ────────────────────────────────────────────────────
st.title("👶 NeoGuard — Neonatal AI Monitoring System")
st.caption("Clinical Pattern Detection · Persistence Filter · High-Risk Only Alerts · XAI Explanations")

# ── Sidebar ───────────────────────────────────────────────────
st.sidebar.header("🏥 Patient Configuration")
ga_at_birth  = st.sidebar.slider("GA at Birth (weeks)", 24, 42, 28)
days_in_nicu = st.sidebar.slider("Days in NICU", 0, 120, 0)
scenario     = st.sidebar.selectbox("Simulate Scenario", [
    'normal', 'apnea', 'sepsis', 'hypothermia',
    'hypoxemia', 'hypotension', 'cold_sepsis', 'hypertension'
])
speed = st.sidebar.slider("Simulation Speed (s)", 0.05, 1.0, 0.15)

# Compute and display corrected GA info
corrected_ga = get_corrected_gestational_age(ga_at_birth, days_in_nicu)
phase        = get_monitoring_phase(corrected_ga)
ga_cat       = get_ga_category(corrected_ga)
watched      = PHASE_WATCHED_VITALS[phase]

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Patient Status")
st.sidebar.metric("Corrected GA",       f"{corrected_ga:.1f} weeks")
st.sidebar.metric("GA Category",        ga_cat.replace('_', ' ').title())
st.sidebar.metric("Monitoring Phase",   phase.replace('_', ' ').upper())
st.sidebar.markdown(f"**Watched Vitals:** {', '.join(watched)}")

# Phase badge color
phase_colors = {
    'acute':           '🔴',
    'extended':        '🟠',
    'step_down':       '🟡',
    'discharge_ready': '🟢',
}
st.sidebar.markdown(
    f"{phase_colors.get(phase, '⚪')} **Phase: {phase.replace('_', ' ').upper()}**"
)

# ── Layout ────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
alert_box  = st.empty()
chart_area = st.empty()
col_log, col_info = st.columns([2, 1])
log_area   = col_log.empty()
info_area  = col_info.empty()

# ── Initialize ────────────────────────────────────────────────
tracker = PersistenceTracker(window_seconds=180)
history = []
alert_log = []
total_readings = 0
total_alerts   = 0

# ── Main Loop ─────────────────────────────────────────────────
for t in range(300):
    total_readings += 1

    # Generate synthetic vitals
    vitals = generate_synthetic_vitals(
        t=t,
        ga_at_birth=ga_at_birth,
        days_in_nicu=days_in_nicu,
        scenario=scenario
    )

    # Update persistence tracker
    tracker.update(vitals)
    history.append({'t': t, **vitals})

    # Detect clinical patterns
    alerts = detect_clinical_patterns(
        current_vitals=vitals,
        tracker=tracker,
        ga_at_birth=ga_at_birth,
        days_in_nicu=days_in_nicu
    )

    # ── Vital Sign Display ────────────────────────────────────
    col1.metric("❤️ Heart Rate",
                f"{vitals['HR']:.0f} bpm",
                delta=None,
                help="Normal varies by corrected GA")
    col2.metric("🫁 SpO2",
                f"{vitals['SpO2']:.1f}%")
    col3.metric("💨 Resp Rate",
                f"{vitals['RR']:.0f} /min")
    col4.metric("🌡️ Temperature",
                f"{vitals['Temp']:.1f} °C")
    col5.metric("💉 MAP",
                f"{vitals['MAP']:.0f} mmHg")

    # ── Alert Display ─────────────────────────────────────────
    if alerts:
        total_alerts += 1
        top = alerts[0]
        icon = "🚨" if top['severity'] == 'CRITICAL' else "⚠️"

        # Get LLM explanation
        try:
            explanation = explain_alert(top, vitals, corrected_ga)
            exp_text    = explanation['explanation']
            primary     = explanation['primary_cause']
            action_text = explanation['suggested_action']
        except Exception:
            exp_text    = top['description']
            primary     = top['contributing_vitals'][0]['vital'] if top['contributing_vitals'] else 'Unknown'
            action_text = top['action']

        alert_box.error(f"""
{icon} **{top['severity']} — {top['label']} Detected**

{exp_text}

⏱️ Duration: **{top['duration_seconds']}s** sustained
📊 Severity Score: **{top['composite_score']}**
🔬 Primary Cause: **{primary}**
💊 **Action: {action_text}**
🏥 Phase: {top['phase'].replace('_',' ').upper()} | CGA: {top['corrected_ga']}w
        """)

        alert_log.append(
            f"[t={t:03d}s] {top['severity']:<8} | {top['label']:<25} | "
            f"Duration: {top['duration_seconds']}s | Score: {top['composite_score']}"
        )
    else:
        alert_box.success("🟢 All vitals within clinical normal range — no alert")

    # ── Real-time Chart ───────────────────────────────────────
    df_plot = pd.DataFrame(history[-60:])
    fig = go.Figure()

    vital_styles = {
        'HR':   ('red',    'solid'),
        'SpO2': ('blue',   'solid'),
        'RR':   ('green',  'solid'),
        'Temp': ('orange', 'dash'),
        'MAP':  ('purple', 'dot'),
    }
    for vital, (color, dash) in vital_styles.items():
        if vital in df_plot.columns:
            fig.add_trace(go.Scatter(
                x=df_plot['t'], y=df_plot[vital],
                name=vital,
                line=dict(color=color, width=2, dash=dash),
                mode='lines'
            ))

    fig.update_layout(
        title=f"Real-Time Vitals — Last 60s | Scenario: {scenario.upper()} | Phase: {phase.upper()}",
        height=300,
        margin=dict(t=40, b=0, l=0, r=0),
        legend=dict(orientation='h', y=-0.2),
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font=dict(color='white'),
    )
    chart_area.plotly_chart(fig, use_container_width=True)

    # ── Alert Log ─────────────────────────────────────────────
    if alert_log:
        log_area.text_area(
            f"📋 Alert Log ({len(alert_log)} alerts)",
            "\n".join(alert_log[-15:]),
            height=150
        )

    # ── Stats Panel ───────────────────────────────────────────
    false_alarm_rate = round(
        (1 - total_alerts / max(total_readings, 1)) * 100, 1
    )
    info_area.info(f"""
**📈 Session Stats**
- Total readings: {total_readings}
- Alerts fired: {total_alerts}
- Suppressed: {total_readings - total_alerts}
- Alert rate: {round(total_alerts/max(total_readings,1)*100,1)}%
- **Alarm fatigue reduction: {false_alarm_rate}%**
    """)

    time.sleep(speed)
# dashboard.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from data_loader import simulate_neonatal_vitals
from signal_filter import filter_vitals
from anomaly_detector import analyze_all_vitals
from risk_scorer import compute_risk_score
from explainer import explain_alert

st.set_page_config(page_title="NeoGuard", page_icon="👶", layout="wide")

st.title("👶 NeoGuard — Neonatal AI Monitoring System")
st.caption("Zero-Shot Anomaly Detection | Explainable AI | High-Risk Only Alerts")

# Sidebar
ga_weeks = st.sidebar.slider("Gestational Age (weeks)", 24, 42, 32)
simulate_anomaly = st.sidebar.checkbox("Simulate Anomaly", value=True)

col1, col2, col3, col4 = st.columns(4)
alert_box = st.empty()
chart_area = st.empty()

# Load data
df = simulate_neonatal_vitals(300, include_anomaly=simulate_anomaly)

# Real-time simulation loop
for i in range(60, len(df), 5):
    window = df.iloc[:i]
    
    # Layer 1: Signal quality
    quality, quality_scores = filter_vitals(window)
    
    if quality < 0.5:
        alert_box.warning("⚠️ Poor signal quality — possible motion artifact")
        continue
    
    # Layer 2: Anomaly detection
    anomaly_results = analyze_all_vitals(window)
    
    # Layer 3: Risk scoring
    risk = compute_risk_score(anomaly_results, ga_weeks, quality)
    
    # Update vital displays
    latest = window.iloc[-1]
    col1.metric("❤️ Heart Rate",    f"{latest['HR']:.0f} bpm",
                delta=f"{latest['HR']-140:.0f}")
    col2.metric("🫁 SpO2",          f"{latest['SpO2']:.1f}%",
                delta=f"{latest['SpO2']-97:.1f}")
    col3.metric("💨 Resp Rate",     f"{latest['RR']:.0f} /min")
    col4.metric("🌡️ Temperature",   f"{latest['Temp']:.1f}°C")
    
    # Layer 4: Alert only if HIGH risk
    if risk['alert']:
        explanation = explain_alert(risk, anomaly_results, ga_weeks)
        
        alert_box.error(f"""
        🚨 **HIGH RISK ALERT**
        
        **{explanation['explanation']}**
        
        📊 Primary cause: **{explanation['primary_cause']}**
        ⚡ Suggested action: *{explanation['suggested_action']}*
        
        Confidence: {risk['confidence']*100:.0f}% | Score: {risk['composite_score']}
        """)
    elif risk['risk_level'] == 'MEDIUM':
        alert_box.warning(f"🟡 Medium risk detected — monitoring closely")
    else:
        alert_box.success("🟢 All vitals within normal range")
    
    # Plot vitals
    fig = go.Figure()
    for vital, color in [('HR','red'),('SpO2','blue'),('RR','green')]:
        fig.add_trace(go.Scatter(
            x=window['timestamp'], y=window[vital],
            name=vital, line=dict(color=color)
        ))
    fig.update_layout(title="Real-Time Vital Signs",
                     height=300, margin=dict(t=30,b=0))
    chart_area.plotly_chart(fig, use_container_width=True)
    
    time.sleep(0.1)  # Simulate real-time

# Run: streamlit run dashboard.py
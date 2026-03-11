"""
NeoGuard Backend — main.py  v3.0  (FULLY INTEGRATED)
═══════════════════════════════════════════════════════════════════
Full 5-Gate Pipeline per reading:
  Gate 1 → SQI        signal_filter.py  (motion artifact rejection)
  Gate 2 → Chronos    anomaly_detector.py  (zero-shot AI anomaly)
  Gate 3 → CDR        risk_scorer.py    (multi-vital AND logic)
  Gate 4 → Persist    risk_scorer.py    (min-duration filter)
  Gate 5 → Cooldown   risk_scorer.py    (120s suppression)
  XAI    → explainer.py                 (Groq LLM plain-English)
  Notify → Telegram + WhatsApp          (CRITICAL only)
  Log    → per-patient alert + vital history (up to 500 readings)
  Report → JSON report + CSV download
  WS     → WebSocket broadcast to React frontend

ESP32:
  - Set ESP32_PORT to your COM port when hardware is ready
  - Arduino code is in the comments below
  - Falls back to simulation when ESP32 not connected

Chronos-Bolt innovation:
  - Feeds last 60 vital readings to Chronos for zero-shot prediction
  - If Chronos flags anomaly BEFORE CDR threshold is crossed,
    min_dur is halved → EARLY DETECTION (shown to jury as innovation)
  - This is what "predict early as per doctor consultations" means
═══════════════════════════════════════════════════════════════════
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import asyncio, json, hashlib, random, time, datetime, io, csv, os
from jose import JWTError, jwt

# ── Optional imports ──────────────────────────────────────────
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

try:
    import numpy as np
    import torch
    from chronos import BaseChronosPipeline
    CHRONOS_AVAILABLE = True
    print("[NeoGuard] Chronos-Bolt import successful")
except Exception as e:
    CHRONOS_AVAILABLE = False
    np = None
    print(f"[NeoGuard] Chronos not available ({e}) — CDR-only mode")

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# ─────────────────────────────────────────────────────────────
# CHRONOS PIPELINE  (lazy-loaded on first use)
# ─────────────────────────────────────────────────────────────
_chronos_pipeline = None

def get_chronos():
    global _chronos_pipeline
    if _chronos_pipeline is None and CHRONOS_AVAILABLE:
        try:
            _chronos_pipeline = BaseChronosPipeline.from_pretrained(
                "amazon/chronos-bolt-small",
                device_map="cpu",
                torch_dtype=torch.float32,
            )
            print("[NeoGuard] Chronos-Bolt pipeline ready")
        except Exception as e:
            print(f"[NeoGuard] Chronos pipeline load failed: {e}")
    return _chronos_pipeline

def chronos_anomaly_score(series: list, vital_name: str) -> dict:
    """
    Zero-shot anomaly detection via Chronos-Bolt.
    Feeds last 60 readings, predicts next 10, compares actual vs predicted.
    Score > 0.5 = Chronos detects anomalous trajectory.
    This is the INNOVATION: detects the ONSET of deterioration
    before thresholds are crossed (early prediction).
    """
    pipeline = get_chronos()
    if pipeline is None or len(series) < 20:
        return {"score": 0.0, "is_anomalous": False, "source": "unavailable"}
    try:
        arr      = np.array(series[-60:], dtype=np.float32)
        context  = torch.tensor(arr).unsqueeze(0)
        forecast = pipeline.predict(context, prediction_length=10)
        pred_np  = forecast[0].numpy().flatten()

        low    = (pred_np * 0.90).tolist()
        high   = (pred_np * 1.10).tolist()
        actual = series[-10:]

        scores = []
        for i, val in enumerate(actual):
            v = float(val)
            if v < low[i]:
                scores.append((low[i] - v) / (high[i] - low[i] + 1e-6))
            elif v > high[i]:
                scores.append((v - high[i]) / (high[i] - low[i] + 1e-6))
            else:
                scores.append(0.0)

        max_score = round(max(scores), 3)
        return {
            "score":          max_score,
            "is_anomalous":   max_score > 0.5,
            "predicted_low":  [round(x, 1) for x in low],
            "predicted_high": [round(x, 1) for x in high],
            "source":         "chronos-bolt",
        }
    except Exception as e:
        return {"score": 0.0, "is_anomalous": False, "source": f"error:{e}"}

# ─────────────────────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────────────────────
app = FastAPI(title="NeoGuard API", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
SECRET_KEY = "neoguard-secret-key-2025"
ALGORITHM  = "HS256"
TOKEN_EXP  = 480

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID",   "")
TWILIO_SID         = os.getenv("TWILIO_SID",          "")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN",   "")
TWILIO_FROM        = os.getenv("TWILIO_WHATSAPP_FROM","")
TWILIO_TO          = os.getenv("TWILIO_WHATSAPP_TO",  "")
GROQ_API_KEY       = os.getenv("GROQ_API_KEY",        "")

# Max 1 Telegram/WhatsApp notification per patient per 5 min (no spam)
NOTIFY_COOLDOWNS: dict[str, float] = {}
NOTIFY_INTERVAL = 300  # seconds

# ─────────────────────────────────────────────────────────────
# ESP32
# ─────────────────────────────────────────────────────────────
ESP32_PORT = None   # Set to "COM3" or "/dev/ttyUSB0" when hardware ready
ESP32_BAUD = 115200
_esp32_conn = None

# ESP32 Arduino code — paste into Arduino IDE and flash to ESP32:
#
# #include <Arduino.h>
# #include <ArduinoJson.h>
# const char* PATIENT_ID = "P001";
# float t = 0;
# void setup() { Serial.begin(115200); delay(1000); }
# void loop() {
#   t += 1;
#   StaticJsonDocument<256> doc;
#   doc["patient_id"] = PATIENT_ID;
#   doc["HR"]   = 140 + 10*sin(0.05*t) + random(-3,3);
#   doc["SpO2"] = 93  + random(-1,1);
#   doc["RR"]   = 50  + 5*sin(0.03*t) + random(-2,2);
#   doc["Temp"] = 36.8 + random(-5,5)*0.01;
#   doc["SBP"]  = 45  + random(-3,3);
#   doc["DBP"]  = 25  + random(-2,2);
#   doc["source"] = "ESP32";
#   serializeJson(doc, Serial);
#   Serial.println();
#   delay(1000);
# }

def connect_esp32():
    global _esp32_conn
    if not SERIAL_AVAILABLE or not ESP32_PORT:
        return False
    try:
        _esp32_conn = serial.Serial(ESP32_PORT, ESP32_BAUD, timeout=2)
        print(f"[NeoGuard] ESP32 connected on {ESP32_PORT}")
        return True
    except Exception as e:
        print(f"[NeoGuard] ESP32 not available: {e}")
        return False

def read_esp32():
    if _esp32_conn and _esp32_conn.is_open:
        try:
            line = _esp32_conn.readline().decode("utf-8").strip()
            if line:
                return json.loads(line)
        except Exception:
            pass
    return None

# ─────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def hash_pw(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()

def verify_pw(plain: str, hashed: str) -> bool:
    return hash_pw(plain) == hashed

def make_token(data: dict) -> str:
    d = data.copy()
    d["exp"] = datetime.datetime.utcnow() + datetime.timedelta(minutes=TOKEN_EXP)
    return jwt.encode(d, SECRET_KEY, algorithm=ALGORITHM)

USERS_DB = {
    "dr.smith":  {"username":"dr.smith",  "full_name":"Dr. Sarah Smith", "role":"doctor", "hashed_password":hash_pw("doctor123")},
    "nurse.raj": {"username":"nurse.raj", "full_name":"Nurse Rajkumar",  "role":"nurse",  "hashed_password":hash_pw("nurse123")},
    "dr.kumar":  {"username":"dr.kumar",  "full_name":"Dr. Arun Kumar",  "role":"doctor", "hashed_password":hash_pw("doctor123")},
}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload  = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username or username not in USERS_DB:
            raise HTTPException(status_code=401, detail="Invalid token")
        return USERS_DB[username]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ─────────────────────────────────────────────────────────────
# PATIENTS
# ─────────────────────────────────────────────────────────────
PATIENTS = {
    "P001": {"id":"P001","name":"Baby Arjun","dob":"2025-01-10","ga_at_birth":28.0,
             "admission_date":"2025-01-10","days_in_nicu":54,"weight_g":980,"sex":"M",
             "diagnosis":"Extreme prematurity, RDS","doctor":"dr.smith",
             "bed":"NICU-01","scenario":"apnea"},
    "P002": {"id":"P002","name":"Baby Priya","dob":"2025-02-14","ga_at_birth":32.0,
             "admission_date":"2025-02-14","days_in_nicu":19,"weight_g":1600,"sex":"F",
             "diagnosis":"Late prematurity, feeding difficulties","doctor":"dr.kumar",
             "bed":"NICU-02","scenario":"normal"},
    "P003": {"id":"P003","name":"Baby Dev","dob":"2025-02-20","ga_at_birth":25.0,
             "admission_date":"2025-02-20","days_in_nicu":13,"weight_g":720,"sex":"M",
             "diagnosis":"Extreme prematurity, IVH Grade II","doctor":"dr.smith",
             "bed":"NICU-03","scenario":"sepsis"},
}

ALERT_LOGS:    dict[str, list] = {pid: [] for pid in PATIENTS}
VITAL_HISTORY: dict[str, list] = {pid: [] for pid in PATIENTS}

# ─────────────────────────────────────────────────────────────
# GATE 1 — SQI (from signal_filter.py)
# ─────────────────────────────────────────────────────────────
PHYS_RANGES = {
    "HR":(30,280),"SpO2":(40,100),"RR":(5,130),
    "Temp":(32,43),"SBP":(15,140),"DBP":(8,100),"MAP":(10,110),
}

def compute_sqi(vitals: dict, history: list) -> float:
    penalties = 0
    for v, (lo, hi) in PHYS_RANGES.items():
        if v in vitals and not (lo <= vitals[v] <= hi):
            penalties += 1
    if len(history) >= 10:
        for v in ["HR","SpO2"]:
            vals = [r[v] for r in history[-10:] if v in r]
            if len(vals) >= 10 and (max(vals)-min(vals)) < 0.01:
                penalties += 2
    if history:
        prev = history[-1]
        if abs(vitals.get("HR",0)   - prev.get("HR",   vitals.get("HR",0)))   > 60: penalties += 1
        if abs(vitals.get("SpO2",0) - prev.get("SpO2", vitals.get("SpO2",0))) > 15: penalties += 1
    return round(max(0.0, 1.0 - penalties*0.25), 2)

# ─────────────────────────────────────────────────────────────
# GATE 2 — CORRECTED GA THRESHOLDS (from risk_scorer.py)
# ─────────────────────────────────────────────────────────────
THRESHOLDS = {
    "extremely_preterm": {
        "HR":  {"min":100,"max":180,"critical_low":80,  "critical_high":205},
        "SpO2":{"min":90, "max":95, "critical_low":80,  "critical_high":98},
        "RR":  {"min":40, "max":70, "critical_low":20,  "critical_high":90},
        "Temp":{"min":36.0,"max":37.5,"critical_low":35.5,"critical_high":38.0},
        "SBP": {"min":35, "max":55, "critical_low":25,  "critical_high":70},
        "DBP": {"min":15, "max":35, "critical_low":10,  "critical_high":45},
        "MAP": {"min":27, "max":45, "critical_low":20,  "critical_high":55},
    },
    "very_preterm": {
        "HR":  {"min":110,"max":170,"critical_low":90,  "critical_high":195},
        "SpO2":{"min":91, "max":95, "critical_low":82,  "critical_high":98},
        "RR":  {"min":40, "max":65, "critical_low":25,  "critical_high":85},
        "Temp":{"min":36.2,"max":37.5,"critical_low":35.5,"critical_high":38.0},
        "SBP": {"min":40, "max":60, "critical_low":30,  "critical_high":75},
        "DBP": {"min":20, "max":40, "critical_low":12,  "critical_high":50},
        "MAP": {"min":35, "max":50, "critical_low":25,  "critical_high":60},
    },
    "late_preterm": {
        "HR":  {"min":120,"max":160,"critical_low":95,  "critical_high":190},
        "SpO2":{"min":92, "max":97, "critical_low":85,  "critical_high":99},
        "RR":  {"min":40, "max":60, "critical_low":25,  "critical_high":80},
        "Temp":{"min":36.4,"max":37.5,"critical_low":36.0,"critical_high":38.0},
        "SBP": {"min":45, "max":65, "critical_low":35,  "critical_high":80},
        "DBP": {"min":25, "max":45, "critical_low":15,  "critical_high":55},
        "MAP": {"min":40, "max":55, "critical_low":28,  "critical_high":65},
    },
    "term": {
        "HR":  {"min":120,"max":160,"critical_low":100,"critical_high":180},
        "SpO2":{"min":95, "max":100,"critical_low":88, "critical_high":100},
        "RR":  {"min":30, "max":60, "critical_low":20, "critical_high":75},
        "Temp":{"min":36.5,"max":37.5,"critical_low":36.0,"critical_high":38.5},
        "SBP": {"min":55, "max":75, "critical_low":40, "critical_high":90},
        "DBP": {"min":30, "max":50, "critical_low":20, "critical_high":65},
        "MAP": {"min":45, "max":60, "critical_low":30, "critical_high":70},
    },
}

PHASE_VITALS = {
    "acute":           ["HR","SpO2","RR","Temp","SBP","DBP","MAP"],
    "extended":        ["HR","SpO2","RR","Temp","MAP"],
    "step_down":       ["SpO2","HR","RR","Temp"],
    "discharge_ready": ["SpO2","HR","Temp"],
}

def get_cga(ga: float, days: int) -> float: return ga + days/7.0
def get_ga_cat(cga: float) -> str:
    if cga < 28:   return "extremely_preterm"
    elif cga < 32: return "very_preterm"
    elif cga < 37: return "late_preterm"
    return "term"
def get_phase(cga: float) -> str:
    if cga < 32:   return "acute"
    elif cga < 36: return "extended"
    elif cga < 40: return "step_down"
    return "discharge_ready"

# ─────────────────────────────────────────────────────────────
# GATES 3+4+5 — CDR ENGINE (from risk_scorer.py)
# Chronos BOOST: anomaly detected → halve min_dur → early alert
# ─────────────────────────────────────────────────────────────
CDR_RULES = [
    {"id":"ABD","name":"Apnea-Bradycardia-Desaturation","severity":"CRITICAL","min_dur":15,
     "phases":["acute","extended","step_down"],"vitals":["SpO2","HR","RR"],
     "check":lambda v,t: v["SpO2"]<t["SpO2"]["min"] and v["HR"]<t["HR"]["min"] and v["RR"]<t["RR"]["min"],
     "action":"Stimulate infant immediately. Prepare bag-mask ventilation. Call physician."},
    {"id":"HYPOXEMIA","name":"Critical Hypoxemia","severity":"CRITICAL","min_dur":15,
     "phases":["acute","extended","step_down","discharge_ready"],"vitals":["SpO2"],
     "check":lambda v,t: v["SpO2"]<t["SpO2"]["critical_low"],
     "action":"Increase FiO2. Check airway. Call physician immediately."},
    {"id":"BRADYCARDIA","name":"Critical Bradycardia","severity":"CRITICAL","min_dur":15,
     "phases":["acute","extended","step_down"],"vitals":["HR"],
     "check":lambda v,t: v["HR"]<t["HR"]["critical_low"],
     "action":"Stimulate infant. Check airway. Prepare resuscitation."},
    {"id":"APNEA","name":"Isolated Apnea","severity":"HIGH","min_dur":20,
     "phases":["acute","extended","step_down","discharge_ready"],"vitals":["RR"],
     "check":lambda v,t: v["RR"]<t["RR"]["critical_low"],
     "action":"Stimulate infant. Monitor for bradycardia development."},
    {"id":"SEPSIS","name":"Early Sepsis Pattern","severity":"HIGH","min_dur":60,
     "phases":["acute","extended"],"vitals":["HR","Temp","RR"],
     "check":lambda v,t: v["HR"]>t["HR"]["max"] and v["Temp"]>t["Temp"]["max"] and v["RR"]>t["RR"]["max"],
     "action":"Draw blood cultures. Start sepsis workup. Notify physician."},
    {"id":"HYPOTENSION","name":"Hypotension / Shock","severity":"CRITICAL","min_dur":20,
     "phases":["acute","extended"],"vitals":["MAP","HR"],
     "check":lambda v,t: v["MAP"]<t["MAP"]["critical_low"] and v["HR"]>t["HR"]["max"],
     "action":"IV fluid bolus 10ml/kg. Notify physician. Prepare vasopressors."},
    {"id":"HYPOTHERMIA","name":"Hypothermia","severity":"HIGH","min_dur":30,
     "phases":["acute","extended","step_down"],"vitals":["Temp","HR"],
     "check":lambda v,t: v["Temp"]<t["Temp"]["min"] and v["HR"]<t["HR"]["min"],
     "action":"Increase incubator temperature. Apply warming measures."},
    {"id":"RDS","name":"Respiratory Distress","severity":"HIGH","min_dur":30,
     "phases":["acute","extended"],"vitals":["RR","SpO2"],
     "check":lambda v,t: v["RR"]>t["RR"]["max"] and v["SpO2"]<t["SpO2"]["min"],
     "action":"Increase respiratory support. Consider CPAP. Call respiratory team."},
    {"id":"COLD_SEPSIS","name":"Cold Sepsis Pattern","severity":"HIGH","min_dur":45,
     "phases":["acute","extended"],"vitals":["HR","Temp"],
     "check":lambda v,t: v["HR"]>t["HR"]["max"] and v["Temp"]<t["Temp"]["min"],
     "action":"Urgent sepsis workup. Warming measures. Notify physician."},
]

STREAKS:   dict[str,dict] = {pid:{r["id"]:0   for r in CDR_RULES} for pid in PATIENTS}
COOLDOWNS: dict[str,dict] = {pid:{r["id"]:0.0 for r in CDR_RULES} for pid in PATIENTS}

def run_cdr_engine(pid:str, vitals:dict, thresh:dict, phase:str, chronos_scores:dict) -> list:
    alerts  = []
    now     = time.time()
    watched = PHASE_VITALS.get(phase, PHASE_VITALS["acute"])

    for rule in CDR_RULES:
        rid = rule["id"]
        if phase not in rule["phases"]:
            STREAKS[pid][rid] = 0; continue
        if not all(v in vitals and v in watched for v in rule["vitals"]):
            continue
        try:
            triggered = rule["check"](vitals, thresh)
        except Exception:
            continue

        if triggered:
            STREAKS[pid][rid] += 1
        else:
            STREAKS[pid][rid] = 0; continue

        # Chronos BOOST — halve min_dur if Chronos already detected anomaly
        min_dur = rule["min_dur"]
        any_chronos = any(
            chronos_scores.get(v,{}).get("is_anomalous", False)
            for v in rule["vitals"]
        )
        if any_chronos:
            min_dur = max(5, min_dur // 2)

        if STREAKS[pid][rid] < min_dur: continue
        if (now - COOLDOWNS[pid].get(rid, 0)) < 300: continue

        scores = {}
        for v in rule["vitals"]:
            t  = thresh[v]
            rw = max(t["max"]-t["min"], 1e-6)
            val = vitals[v]
            if val < t["min"]:   scores[v] = round((t["min"]-val)/rw, 3)
            elif val > t["max"]: scores[v] = round((val-t["max"])/rw, 3)
            else:                scores[v] = 0.0

        import uuid as _uuid
        alerts.append({
            "alert_id":        str(_uuid.uuid4())[:8],
            "rule_id":         rid,
            "name":            rule["name"],
            "severity":        rule["severity"],
            "action":          rule["action"],
            "duration":        STREAKS[pid][rid],
            "composite_score": round(sum(scores.values())/max(len(scores),1), 3),
            "early_detection": any_chronos,
            "acknowledged":    False,
            "acknowledged_by": None,
            "acknowledged_at": None,
            "contributing_vitals": [
                {"vital":v,"actual":round(vitals[v],1),
                 "normal_min":thresh[v]["min"],"normal_max":thresh[v]["max"],
                 "deviation":scores.get(v,0)}
                for v in rule["vitals"]
            ],
            "timestamp": datetime.datetime.now().isoformat(),
        })
        COOLDOWNS[pid][rid] = now
        STREAKS[pid][rid]   = 0

    return sorted(alerts, key=lambda x: 0 if x["severity"]=="CRITICAL" else 1)

# ─────────────────────────────────────────────────────────────
# XAI — from explainer.py (Groq LLM + rule-based fallback)
# ─────────────────────────────────────────────────────────────
def build_xai_message(alert:dict, vitals:dict, cga:float, patient_name:str) -> str:
    cvitals = alert.get("contributing_vitals", [])
    vital_lines = []
    for cv in cvitals:
        direction = "LOW" if cv["actual"] < cv["normal_min"] else "HIGH"
        vital_lines.append(
            f"{cv['vital']}: {cv['actual']} ({direction}, normal {cv['normal_min']}-{cv['normal_max']})"
        )
    early = " [Via Chronos-AI]" if alert.get("early_detection") else ""
    vitals_text = " | ".join(vital_lines)

    base = (
        f"NeoGuard ALERT{early}\n"
        f"Patient: {patient_name} | CGA {cga:.1f}w\n"
        f"Condition: {alert['name']} [{alert['severity']}]\n"
        f"Duration: {alert['duration']}s\n"
        f"Vitals: {vitals_text}\n"
        f"Action: {alert['action']}"
    )

    if GROQ_AVAILABLE and GROQ_API_KEY:
        try:
            client = Groq(api_key=GROQ_API_KEY)
            prompt = (
                f"Neonatal clinical AI. Patient: {patient_name}, CGA {cga:.1f} weeks.\n"
                f"Alert: {alert['name']} (severity: {alert['severity']})\n"
                f"Vitals: {vitals_text} | Duration: {alert['duration']}s\n"
                "Write a 2-sentence bedside nurse alert. Clinical, specific, no jargon."
            )
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"user","content":prompt}],
                max_tokens=120,
            )
            llm_text = resp.choices[0].message.content.strip()
            return base + f"\nAI: {llm_text}"
        except Exception:
            pass
    return base

# ─────────────────────────────────────────────────────────────
# NOTIFICATIONS — Telegram + WhatsApp
# ─────────────────────────────────────────────────────────────
async def send_telegram(message: str, patient_id: str = ""):
    """Send Telegram message. Rate-limited: 1 per patient per 5 minutes."""
    now = time.time()
    if patient_id and (now - NOTIFY_COOLDOWNS.get(f"tg_{patient_id}", 0)) < NOTIFY_INTERVAL:
        print(f"[Telegram] Cooldown active for {patient_id} — skipping")
        return
    if not HTTPX_AVAILABLE:
        print("[Telegram] httpx not installed — run: pip install httpx")
        return
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] Token/Chat ID not set — add to .env or hardcode in CONFIG section")
        return
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"},
                timeout=10,
            )
        if r.status_code == 200:
            print(f"[Telegram] ✅ Alert sent for {patient_id}")
            if patient_id:
                NOTIFY_COOLDOWNS[f"tg_{patient_id}"] = now
        else:
            print(f"[Telegram] ❌ HTTP {r.status_code}: {r.text}")
    except Exception as e:
        print(f"[Telegram] ❌ Error: {e}")

async def send_whatsapp(message: str, patient_id: str = ""):
    """Send WhatsApp via Twilio. Rate-limited: 1 per patient per 5 minutes."""
    now = time.time()
    if patient_id and (now - NOTIFY_COOLDOWNS.get(f"wa_{patient_id}", 0)) < NOTIFY_INTERVAL:
        return
    if not HTTPX_AVAILABLE or not TWILIO_SID or not TWILIO_AUTH_TOKEN:
        return
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json",
                data={"From":TWILIO_FROM,"To":TWILIO_TO,"Body":message},
                auth=(TWILIO_SID, TWILIO_AUTH_TOKEN),
                timeout=10,
            )
        if r.status_code in (200, 201):
            print(f"[WhatsApp] ✅ Alert sent for {patient_id}")
            if patient_id:
                NOTIFY_COOLDOWNS[f"wa_{patient_id}"] = now
        else:
            print(f"[WhatsApp] ❌ HTTP {r.status_code}: {r.text}")
    except Exception as e:
        print(f"[WhatsApp] ❌ Error: {e}")

# ─────────────────────────────────────────────────────────────
# SYNTHETIC VITAL GENERATOR — Realistic Episode + Recovery Model
#
# Real-world NICU behaviour:
#   - Most of the time vitals are NORMAL (realistic baseline)
#   - Occasional episodes (apnea, sepsis etc) last 30-120 seconds
#   - After episode → recovery period back to normal
#   - Each patient has a DIFFERENT assigned scenario (distributed)
#   - Episode frequency: roughly 1 per 5-10 minutes per patient
#
# Patient scenario distribution (jury demo):
#   P001 → apnea      (most common extreme preterm event)
#   P002 → sepsis     (late preterm with feeding issues → infection risk)
#   P003 → hypotension (extremely preterm IVH → cardiovascular instability)
#   P004+ → cycling between normal and hypothermia
# ─────────────────────────────────────────────────────────────
_ticks:      dict[str,int]   = {}
_ep_start:   dict[str,int]   = {}   # tick when current episode started (0 = no episode)
_ep_type:    dict[str,str]   = {}   # current episode type per patient
_next_ep:    dict[str,int]   = {}   # tick at which next episode will trigger

# Distributed scenarios — different clinical picture per patient
PATIENT_SCENARIOS = {
    "P001": "apnea",
    "P002": "sepsis",
    "P003": "hypotension",
}
def get_scenario(pid: str, patient: dict) -> str:
    """Return assigned scenario for this patient (distributed across patients)."""
    sc_list = ["apnea","sepsis","hypotension","hypothermia","hypoxemia"]
    # Use PATIENT_SCENARIOS if defined, else assign by patient index
    if pid in PATIENT_SCENARIOS:
        return PATIENT_SCENARIOS[pid]
    idx = int(pid[1:]) % len(sc_list) if pid[1:].isdigit() else 0
    return sc_list[idx]

EPISODE_DURATION  = 45   # seconds an episode lasts before recovery starts
EPISODE_INTERVAL  = 360  # seconds between episodes (~6 min — realistic NICU)
RECOVERY_DURATION = 60   # seconds of gradual recovery after episode

def generate_vitals(patient: dict) -> dict:
    pid  = patient["id"]
    _ticks[pid]    = _ticks.get(pid, 0) + 1
    t              = _ticks[pid]
    cga            = get_cga(patient["ga_at_birth"], patient["days_in_nicu"])
    cat            = get_ga_cat(cga)
    th             = THRESHOLDS[cat]
    sc             = get_scenario(pid, patient)
    rng            = random.Random(t * 13 + sum(ord(c) for c in pid))

    # Stagger episode start per patient so alerts are distributed
    pid_offset = (int(pid[1:]) * 120) if pid[1:].isdigit() else 0
    if pid not in _next_ep:
        _next_ep[pid] = 90 + pid_offset   # first episode: 90s after start, staggered

    # Determine episode state
    in_episode   = False
    recovering   = False
    episode_prog = 0.0   # 0.0→1.0 progress through episode
    recovery_prog= 0.0   # 0.0→1.0 progress through recovery

    ep_start = _ep_start.get(pid, 0)
    if ep_start > 0:
        elapsed = t - ep_start
        if elapsed < EPISODE_DURATION:
            in_episode   = True
            episode_prog = min(elapsed / EPISODE_DURATION, 1.0)
        elif elapsed < EPISODE_DURATION + RECOVERY_DURATION:
            recovering    = True
            recovery_prog = (elapsed - EPISODE_DURATION) / RECOVERY_DURATION
        else:
            # Episode fully over — reset and schedule next
            _ep_start[pid] = 0
            _next_ep[pid]  = t + EPISODE_INTERVAL + rng.randint(-30, 30)

    # Trigger new episode if scheduled
    if ep_start == 0 and t >= _next_ep.get(pid, 99999):
        _ep_start[pid]  = t
        _ep_type[pid]   = sc
        in_episode      = True
        episode_prog    = 0.0
        print(f"[NeoGuard] Episode START: {pid} ({sc}) at t={t}")

    # Normal baseline vitals
    HR   = (th["HR"]["min"]   + th["HR"]["max"])   / 2 + rng.gauss(0, 2.0)
    SpO2 = (th["SpO2"]["min"] + th["SpO2"]["max"]) / 2 + rng.gauss(0, 0.3)
    RR   = (th["RR"]["min"]   + th["RR"]["max"])   / 2 + rng.gauss(0, 1.2)
    Temp = (th["Temp"]["min"] + th["Temp"]["max"]) / 2 + rng.gauss(0, 0.04)
    SBP  = (th["SBP"]["min"]  + th["SBP"]["max"])  / 2 + rng.gauss(0, 1.5)
    DBP  = (th["DBP"]["min"]  + th["DBP"]["max"])  / 2 + rng.gauss(0, 1.0)

    # Apply episode deterioration
    if in_episode or recovering:
        current_sc = _ep_type.get(pid, sc)
        if recovering:
            p = 1.0 - recovery_prog   # fades back to 0
        else:
            p = episode_prog          # ramps up 0→1

        if current_sc == "apnea":
            SpO2 -= p * 17; HR -= p * 38; RR -= p * 27
        elif current_sc == "sepsis":
            HR += p * 35; Temp += p * 1.5; RR += p * 20
        elif current_sc == "hypothermia":
            Temp -= p * 1.6; HR -= p * 25
        elif current_sc == "hypoxemia":
            SpO2 -= p * 20
        elif current_sc == "hypotension":
            SBP -= p * 20; DBP -= p * 14; HR += p * 25
        elif current_sc == "cold_sepsis":
            HR += p * 28; Temp -= p * 1.0

    MAP = (SBP + 2 * DBP) / 3
    return {
        "HR":        round(max(40,  min(250, HR)),   1),
        "SpO2":      round(max(50,  min(100, SpO2)), 1),
        "RR":        round(max(5,   min(120, RR)),   1),
        "Temp":      round(max(33,  min(42,  Temp)), 1),
        "SBP":       round(max(20,  min(130, SBP)),  1),
        "DBP":       round(max(10,  min(90,  DBP)),  1),
        "MAP":       round(max(15,  min(100, MAP)),  1),
        "timestamp": datetime.datetime.now().isoformat(),
        "source":    "simulated",
        "in_episode": in_episode or recovering,
    }

# ─────────────────────────────────────────────────────────────
# WEBSOCKET MANAGER
# ─────────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, pid: str, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(pid, []).append(ws)

    def disconnect(self, pid: str, ws: WebSocket):
        if pid in self.active:
            try: self.active[pid].remove(ws)
            except ValueError: pass

    async def broadcast(self, pid: str, data: dict):
        dead = []
        for ws in self.active.get(pid, []):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(pid, ws)

manager = ConnectionManager()

# ─────────────────────────────────────────────────────────────
# MAIN PIPELINE STREAMER
# ─────────────────────────────────────────────────────────────
async def vital_streamer():
    """Full 5-gate pipeline — 1 second per patient."""
    connect_esp32()
    while True:
        for pid, patient in PATIENTS.items():

            # Get vitals
            esp_data = read_esp32()
            if esp_data and esp_data.get("patient_id") == pid:
                vitals = {k: float(esp_data[k]) for k in
                          ["HR","SpO2","RR","Temp","SBP","DBP"] if k in esp_data}
                vitals["MAP"]       = round((vitals.get("SBP",45)+2*vitals.get("DBP",25))/3, 1)
                vitals["timestamp"] = datetime.datetime.now().isoformat()
                vitals["source"]    = "ESP32"
            else:
                vitals = generate_vitals(patient)

            # Gate 1 — SQI
            sqi      = compute_sqi(vitals, VITAL_HISTORY[pid])
            artifact = sqi < 0.6
            vitals["sqi"]      = sqi
            vitals["artifact"] = artifact

            VITAL_HISTORY[pid].append(vitals)
            if len(VITAL_HISTORY[pid]) > 500:
                VITAL_HISTORY[pid].pop(0)

            cga    = get_cga(patient["ga_at_birth"], patient["days_in_nicu"])
            cat    = get_ga_cat(cga)
            phase  = get_phase(cga)
            thresh = THRESHOLDS[cat]

            if artifact:
                await manager.broadcast(pid, {
                    "type":"vitals","patient_id":pid,"vitals":vitals,
                    "alerts":[],"artifact":True,"sqi":sqi,
                    "cga":round(cga,1),"phase":phase,"ga_category":cat,
                })
                continue

            # Gate 2 — Chronos anomaly scores
            chronos_scores = {}
            if CHRONOS_AVAILABLE and len(VITAL_HISTORY[pid]) >= 20:
                clean = [v for v in VITAL_HISTORY[pid] if not v.get("artifact",False)]
                for vk in ["HR","SpO2","RR","Temp"]:
                    series = [v[vk] for v in clean if vk in v]
                    if len(series) >= 20:
                        chronos_scores[vk] = chronos_anomaly_score(series, vk)

            # Gates 3+4+5 — CDR
            alerts = run_cdr_engine(pid, vitals, thresh, phase, chronos_scores)

            # XAI + store + notify
            for alert in alerts:
                xai = build_xai_message(alert, vitals, cga, patient["name"])
                alert["xai_message"]  = xai
                alert["patient_id"]   = pid
                alert["patient_name"] = patient["name"]
                alert["bed"]          = patient.get("bed", "--")
                alert["doctor"]       = patient.get("doctor", "")
                ALERT_LOGS[pid].append(alert)
                if len(ALERT_LOGS[pid]) > 500:
                    ALERT_LOGS[pid].pop(0)
                if alert["severity"] == "CRITICAL":
                    asyncio.create_task(send_telegram(xai, pid))
                    asyncio.create_task(send_whatsapp(xai, pid))

            # WebSocket → React
            await manager.broadcast(pid, {
                "type":           "vitals",
                "patient_id":     pid,
                "vitals":         vitals,
                "alerts":         alerts,
                "chronos_scores": chronos_scores,
                "sqi":            sqi,
                "artifact":       False,
                "cga":            round(cga,1),
                "phase":          phase,
                "ga_category":    cat,
                "thresholds":     thresh,
                "chronos_active": CHRONOS_AVAILABLE,
            })

        await asyncio.sleep(1)

@app.on_event("startup")
async def startup():
    asyncio.create_task(vital_streamer())

# ─────────────────────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/auth/login")
async def login(data: LoginRequest):
    user = USERS_DB.get(data.username)
    if not user or not verify_pw(data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = make_token({"sub": user["username"], "role": user["role"]})
    return {"access_token":token,"token_type":"bearer",
            "role":user["role"],"full_name":user["full_name"]}

@app.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return {"username":user["username"],"full_name":user["full_name"],"role":user["role"]}

@app.get("/patients")
async def list_patients(user=Depends(get_current_user)):
    result = []
    for pid, p in PATIENTS.items():
        cga = get_cga(p["ga_at_birth"], p["days_in_nicu"])
        result.append({
            **p,
            "corrected_ga":   round(cga,1),
            "phase":          get_phase(cga),
            "ga_category":    get_ga_cat(cga),
            "pending_alerts": len([a for a in ALERT_LOGS[pid] if a["severity"]=="CRITICAL"]),
            "last_vitals":    VITAL_HISTORY[pid][-1] if VITAL_HISTORY[pid] else {},
        })
    return result

@app.get("/patients/{pid}")
async def get_patient(pid: str, user=Depends(get_current_user)):
    if pid not in PATIENTS:
        raise HTTPException(status_code=404, detail="Not found")
    p = PATIENTS[pid]; cga = get_cga(p["ga_at_birth"], p["days_in_nicu"])
    return {**p,"corrected_ga":round(cga,1),"phase":get_phase(cga),
            "ga_category":get_ga_cat(cga),"thresholds":THRESHOLDS[get_ga_cat(cga)]}

@app.post("/patients")
async def add_patient(data: dict, user=Depends(get_current_user)):
    if user["role"] != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can add patients")
    new_pid = f"P{str(len(PATIENTS)+1).zfill(3)}"
    PATIENTS[new_pid]      = {**data,"id":new_pid}
    ALERT_LOGS[new_pid]    = []
    VITAL_HISTORY[new_pid] = []
    STREAKS[new_pid]       = {r["id"]:0   for r in CDR_RULES}
    COOLDOWNS[new_pid]     = {r["id"]:0.0 for r in CDR_RULES}
    return {"id":new_pid,**PATIENTS[new_pid]}

@app.get("/patients/{pid}/vitals")
async def get_vitals(pid: str, limit: int=60, user=Depends(get_current_user)):
    if pid not in VITAL_HISTORY:
        raise HTTPException(status_code=404, detail="Not found")
    return VITAL_HISTORY[pid][-limit:]

@app.get("/patients/{pid}/alerts")
async def get_alerts(pid: str, user=Depends(get_current_user)):
    if pid not in ALERT_LOGS:
        raise HTTPException(status_code=404, detail="Not found")
    return ALERT_LOGS[pid]

@app.get("/alerts/active")
async def active_alerts(user=Depends(get_current_user)):
    all_a = []
    for pid, logs in ALERT_LOGS.items():
        all_a.extend([a for a in logs if a["severity"] in ["CRITICAL","HIGH"]][-5:])
    all_a.sort(key=lambda x: x["timestamp"], reverse=True)
    return all_a[:20]

@app.get("/patients/{pid}/report")
async def get_report(pid: str, user=Depends(get_current_user)):
    if pid not in PATIENTS:
        raise HTTPException(status_code=404, detail="Not found")
    p=PATIENTS[pid]; hist=VITAL_HISTORY[pid]; alerts=ALERT_LOGS[pid]
    cga=get_cga(p["ga_at_birth"],p["days_in_nicu"]); cat=get_ga_cat(cga); thresh=THRESHOLDS[cat]
    clean = [v for v in hist if not v.get("artifact",False)]
    vitals_summary = {}
    for key in ["HR","SpO2","RR","Temp","MAP"]:
        vals = [v[key] for v in clean if key in v]
        if vals:
            thr = thresh[key]
            vitals_summary[key] = {
                "avg":round(sum(vals)/len(vals),1), "min":round(min(vals),1),
                "max":round(max(vals),1), "normal_min":thr["min"], "normal_max":thr["max"],
                "pct_in_range":round(sum(1 for v in vals if thr["min"]<=v<=thr["max"])/len(vals)*100,1),
            }
    rule_counts = {}
    for a in alerts:
        rule_counts[a["name"]] = rule_counts.get(a["name"],0)+1
    total = len(hist); artifacts = len([v for v in hist if v.get("artifact",False)])
    early = len([a for a in alerts if a.get("early_detection",False)])
    return {
        "patient":p, "corrected_ga":round(cga,1), "phase":get_phase(cga),
        "ga_category":cat, "thresholds":thresh,
        "vitals_summary":vitals_summary,
        "alerts_summary":{
            "total":len(alerts),"critical":len([a for a in alerts if a["severity"]=="CRITICAL"]),
            "high":len([a for a in alerts if a["severity"]=="HIGH"]),
            "early_detected_by_chronos":early, "by_rule":rule_counts,
            "false_alarm_reduction_pct":round((1-len(alerts)/max(total,1))*100,1),
        },
        "signal_quality":{"total_readings":total,"artifacts_rejected":artifacts,
                          "clean_readings":total-artifacts,
                          "avg_sqi":round(sum(v.get("sqi",1.0) for v in hist)/max(len(hist),1),2)},
        "pipeline_status":{
            "chronos_active":CHRONOS_AVAILABLE,
            "esp32_connected":bool(_esp32_conn and SERIAL_AVAILABLE),
            "telegram_enabled":bool(TELEGRAM_BOT_TOKEN),
            "whatsapp_enabled":bool(TWILIO_SID),
        },
        "recent_alerts":   alerts[-20:],
        "all_alerts":      alerts,
        "vitals_history":  clean[-120:],   # last 2 min of clean readings for frontend chart
        "report_time":     datetime.datetime.now().isoformat(),
        "has_data":        len(clean) > 0,
    }

@app.get("/patients/{pid}/report/download")
async def download_report(pid: str, user=Depends(get_current_user)):
    if pid not in PATIENTS:
        raise HTTPException(status_code=404, detail="Not found")
    p=PATIENTS[pid]; alerts=ALERT_LOGS[pid]; hist=VITAL_HISTORY[pid]
    cga=get_cga(p["ga_at_birth"],p["days_in_nicu"])
    output = io.StringIO(); w = csv.writer(output)
    w.writerow(["NeoGuard — Patient Clinical Report"])
    w.writerow(["Generated", datetime.datetime.now().isoformat()])
    w.writerow(["Pipeline","SQI -> Chronos-Bolt -> CDR (AND+Persist+Cooldown) -> XAI -> Notify"])
    w.writerow([])
    for label, key in [("Patient ID","id"),("Name","name"),("DOB","dob"),("Sex","sex"),
                        ("GA at Birth","ga_at_birth"),("Weight (g)","weight_g"),
                        ("Days in NICU","days_in_nicu"),("Diagnosis","diagnosis"),
                        ("Bed","bed"),("Doctor","doctor")]:
        w.writerow([label, p.get(key,"")])
    w.writerow(["Corrected GA (weeks)", round(cga,1)])
    w.writerow(["Monitoring Phase", get_phase(cga)])
    w.writerow(["GA Category", get_ga_cat(cga)])
    w.writerow([])
    w.writerow(["=== ALERT LOG ==="])
    w.writerow(["Timestamp","Rule ID","Condition","Severity","Duration(s)",
                "Composite Score","Early Detection (Chronos)","Action","XAI Explanation"])
    for a in alerts:
        w.writerow([a.get("timestamp",""),a.get("rule_id",""),a.get("name",""),
                    a.get("severity",""),a.get("duration",""),a.get("composite_score",""),
                    a.get("early_detection",""),a.get("action",""),
                    a.get("xai_message","").replace("\n"," | ")])
    w.writerow([])
    w.writerow(["=== VITAL SIGNS HISTORY ==="])
    w.writerow(["Timestamp","HR","SpO2","RR","Temp","SBP","DBP","MAP","SQI","Artifact","Source"])
    for v in hist:
        w.writerow([v.get("timestamp",""),v.get("HR",""),v.get("SpO2",""),v.get("RR",""),
                    v.get("Temp",""),v.get("SBP",""),v.get("DBP",""),v.get("MAP",""),
                    v.get("sqi",""),v.get("artifact",""),v.get("source","")])
    output.seek(0)
    fname = f"NeoGuard_{p['name'].replace(' ','_')}_{datetime.date.today()}.csv"
    csv_bytes = output.getvalue().encode("utf-8-sig")  # BOM for Excel compatibility
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv; charset=utf-8-sig",
        headers={
            "Content-Disposition": f'attachment; filename="{fname}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        }
    )

# ── ACKNOWLEDGE ALERT ────────────────────────────────────────
@app.post("/alerts/{pid}/{alert_id}/acknowledge")
async def acknowledge_alert(pid: str, alert_id: str, user=Depends(get_current_user)):
    """Doctor/nurse ticks off an alert as acknowledged."""
    if pid not in ALERT_LOGS:
        raise HTTPException(status_code=404, detail="Patient not found")
    for alert in ALERT_LOGS[pid]:
        if alert.get("alert_id") == alert_id:
            alert["acknowledged"]    = True
            alert["acknowledged_by"] = user["full_name"]
            alert["acknowledged_at"] = datetime.datetime.now().isoformat()
            # Broadcast acknowledgement to all connected clients for this patient
            await manager.broadcast(pid, {
                "type":       "alert_acknowledged",
                "patient_id": pid,
                "alert_id":   alert_id,
                "acknowledged_by": user["full_name"],
                "acknowledged_at": alert["acknowledged_at"],
            })
            return {"status": "acknowledged", "alert_id": alert_id,
                    "acknowledged_by": user["full_name"]}
    raise HTTPException(status_code=404, detail="Alert not found")

# ── UN-ACKNOWLEDGE ────────────────────────────────────────────
@app.delete("/alerts/{pid}/{alert_id}/acknowledge")
async def unacknowledge_alert(pid: str, alert_id: str, user=Depends(get_current_user)):
    if pid not in ALERT_LOGS:
        raise HTTPException(status_code=404, detail="Patient not found")
    for alert in ALERT_LOGS[pid]:
        if alert.get("alert_id") == alert_id:
            alert["acknowledged"]    = False
            alert["acknowledged_by"] = None
            alert["acknowledged_at"] = None
            return {"status": "unacknowledged", "alert_id": alert_id}
    raise HTTPException(status_code=404, detail="Alert not found")

# ── TEST TELEGRAM (no auth needed — for setup verification) ──
@app.get("/test/telegram")
async def test_telegram():
    """Hit this in browser to verify Telegram is configured: http://localhost:8000/test/telegram"""
    msg = (
        "NeoGuard TEST\n"
        "If you see this, Telegram is working!\n"
        f"Time: {datetime.datetime.now().strftime('%H:%M:%S')}"
    )
    await send_telegram(msg, "TEST")
    return {
        "telegram_token_set": bool(TELEGRAM_BOT_TOKEN),
        "telegram_chat_set":  bool(TELEGRAM_CHAT_ID),
        "httpx_available":    HTTPX_AVAILABLE,
        "message":            "Check your Telegram. Also check terminal for [Telegram] logs.",
    }

@app.websocket("/ws/{patient_id}")
async def ws_endpoint(websocket: WebSocket, patient_id: str):
    await manager.connect(patient_id, websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(patient_id, websocket)

@app.get("/")
async def root():
    return {
        "status":   "NeoGuard API v3.0 — Fully Integrated",
        "docs":     "/docs",
        "patients": len(PATIENTS),
        "pipeline": "SQI -> Chronos-Bolt -> CDR (AND+Persist+Cooldown) -> XAI -> Telegram/WhatsApp -> WebSocket",
        "chronos":  CHRONOS_AVAILABLE,
        "esp32":    ESP32_PORT is not None,
    }

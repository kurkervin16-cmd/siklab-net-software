## Setup
pip install tensorflow flask flask-socketio numpy requests
python app.py → http://localhost:5000

## Demo
1. Open dashboard
2. Click Trigger Storm Event
3. Watch AI shed non-critical loads — IRON tier stays ON

## Stack
Keras LSTM | NASA POWER LARC | Flask + Socket.IO
RMSE: 29.22 W/m² | MAE: 15.79 W/m²

# ⚡ SIKLAB Net — Edge AI Grid Controller

> **Offline-first, predictive microgrid load-shedding powered by TensorFlow Lite.**  
> *Preserving critical community infrastructure (vaccine cold storage, emergency comms, water pumps) during grid failures and severe weather.*

---

## 📌 Problem & Solution

During severe weather or grid failures, standard backup solar microgrids drain their batteries within 2–3 hours by trying to power all loads equally. 

**SIKLAB Net** uses an embedded **TensorFlow Lite (TFLite)** model running locally on an edge controller (Raspberry Pi/ESP32). It forecasts 24-hour solar generation trends and dynamically sheds non-essential electrical loads *before* the battery drains—stretching critical operational lifelines up to **24+ hours**.

---

## 🚀 Key Features

* **100% Offline / Edge AI:** Runs fully local without requiring cloud access, cellular signals, or internet connectivity.
* **Predictive Load Triage:** Analyzes solar irradiance trends to proactively manage battery State of Charge ($\text{SoC}$).
* **Multi-Tier Load Shedding:**
  * 🔴 **IRON Tier (Always ON):** Vaccine refrigeration, emergency communication, water pumps.
  * 🟡 **PRIORITY Tier (Conditional):** Health center outlets, municipal office logic.
  * 🟢 **DEFERRABLE Tier (First to Shed):** Residential sectors and commercial loads.
* **Real-Time WebSocket Control:** Low-latency dynamic telemetry streaming and manual relay override dashboard.

---

## 🛠️ System Architecture

```text
[Solar Panel / Batt Sensors] 
       │ (I2C / ADC)
       ▼
[Microcontroller (ESP32)] ──(USB Serial)──► [Raspberry Pi (Master)]
                                                   │
                                            (TFLite Model)
                                                   │
                                            (Relay Signal)
                                                   ▼
                                         [4-Channel Relays]
                                         ├── 🔴 Iron Tier
                                         ├── 🟡 Priority Tier
                                         └── 🟢 Deferrable Tier

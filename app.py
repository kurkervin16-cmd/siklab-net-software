from flask import Flask, render_template
from flask_socketio import SocketIO
import threading
import time

# =====================================================
# DATA SOURCE
# =====================================================
# False = Use simulator (current setup)
# True  = Use real hardware sensors
# =====================================================

USE_HARDWARE = False

if USE_HARDWARE:
    from hardware import snapshot
else:
    from simulator import snapshot, scenario

from decision_engine import (
    predict_next_hour,
    compute_survival_window,
    run_triage,
)

# =====================================================
# FLASK
# =====================================================

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# =====================================================
# GLOBAL VARIABLES
# =====================================================

step = 0
irr_window = [300.0] * 24

MODE_COLORS = {
    "NORMAL": "#2ecc71",
    "CONSERVATION": "#f39c12",
    "CRITICAL": "#e74c3c",
}

# =====================================================
# ROUTES
# =====================================================

@app.route("/")
def index():
    return render_template("dashboard.html")

# =====================================================
# SOCKET EVENTS
# =====================================================

# Only needed when running the simulator
if not USE_HARDWARE:

    @socketio.on("change_scenario")
    def handle_change_scenario(data):
        scenario["type"] = data.get("event", "normal")
        print(f"Scenario changed to: {scenario['type']}")

# =====================================================
# MAIN LOOP
# =====================================================

def loop():
    global step, irr_window

    while True:

        # -----------------------------
        # Get latest system snapshot
        # -----------------------------
        try:
            snap = snapshot(step)
        except TypeError:
            # hardware.py snapshot() may not need "step"
            snap = snapshot()

        # -----------------------------
        # AI Prediction
        # -----------------------------
        irr_window = (irr_window + [snap["solar_w"]])[-24:]

        predicted_w = predict_next_hour(irr_window)

        sw = compute_survival_window(
            snap["battery_soc"],
            snap["iron_w"],
        )

        mode = run_triage(sw)

        # -----------------------------
        # Send to Dashboard
        # -----------------------------
        socketio.emit(
            "update",
            {
                **snap,
                "sw": sw,
                "mode": mode,
                "mode_color": MODE_COLORS[mode],
                "predicted_w": round(predicted_w, 1),
            },
        )

        step += 1
        time.sleep(3)

# =====================================================
# START BACKGROUND THREAD
# =====================================================

threading.Thread(target=loop, daemon=True).start()

# =====================================================
# START SERVER
# =====================================================

if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=False,
        allow_unsafe_werkzeug=True,
    )
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import threading, time
from simulator import snapshot, scenario
from decision_engine import predict_next_hour, compute_survival_window, run_triage

app      = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

step, irr_window = 0, [300.0] * 24
MODE_COLORS = {
    "NORMAL":       "#2ecc71",
    "CONSERVATION": "#f39c12",
    "CRITICAL":     "#e74c3c"
}

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/trigger", methods=["POST"])
def trigger():
    scenario["type"] = request.json.get("event", "normal")
    return jsonify({"ok": True})

def loop():
    global step, irr_window
    while True:
        snap        = snapshot(step)
        irr_window  = (irr_window + [snap["solar_w"]])[-24:]
        predicted_w = predict_next_hour(irr_window)
        sw          = compute_survival_window(snap["battery_soc"], snap["iron_w"])
        mode        = run_triage(sw)

        socketio.emit("update", {
            **snap,
            "sw":          sw,
            "mode":        mode,
            "mode_color":  MODE_COLORS[mode],
            "predicted_w": round(predicted_w, 1),
        })
        step += 1
        time.sleep(3)

threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)

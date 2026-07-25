import numpy as np
import tensorflow as tf
from simulator import set_relay

# Initialize the ultra-lightweight TFLite interpreter
interpreter = tf.lite.Interpreter(model_path="model/siklab_model.tflite")
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

X_MAX = float(np.load("model/x_max.npy"))

BATTERY_WH = 5000
SW_AMBER   = 4.0
SW_RED     = 2.0

def predict_next_hour(last_24):
    # Normalize and reshape to the exact (1, 24, 1) shape required
    data = (np.array(last_24, dtype=np.float32) / X_MAX).reshape(1, 24, 1)

    # Set tensor input and execute computational graph
    interpreter.set_tensor(input_details[0]['index'], data)
    interpreter.invoke()
    raw_pred = interpreter.get_tensor(output_details[0]['index'])[0][0]

    # Rescale back to true wattage and clamp at 0.0 to fix the negative nighttime bug
    return max(0.0, float(raw_pred) * X_MAX)

def compute_survival_window(soc_pct, iron_w):
    remaining_wh = BATTERY_WH * (soc_pct / 100)
    return round(remaining_wh / iron_w, 2) if iron_w > 0 else 99.0

def run_triage(sw):
    defer_keys    = ["defer_residential_a","defer_residential_b","defer_commercial"]
    priority_keys = ["priority_health","priority_gov"]
    if sw > SW_AMBER:
        for k in priority_keys + defer_keys: set_relay(k, True)
        return "NORMAL"
    elif sw > SW_RED:
        for k in priority_keys: set_relay(k, True)
        for k in defer_keys:    set_relay(k, False)
        return "CONSERVATION"
    else:
        for k in priority_keys + defer_keys: set_relay(k, False)
        return "CRITICAL"

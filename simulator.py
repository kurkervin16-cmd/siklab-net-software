import json, numpy as np
from datetime import datetime

with open("data/solar_data.json") as f:
    raw = json.load(f)
irr_values = [max(0, v) for v in raw.values()]

relay_states = {
    "iron_vaccine":        True,
    "iron_water_pump":     True,
    "iron_comms":          True,
    "priority_health":     True,
    "priority_gov":        True,
    "defer_residential_a": True,
    "defer_residential_b": True,
    "defer_commercial":    True,
}

battery = {"soc_pct": 80.0, "voltage_v": 12.5, "capacity_wh": 5000}
scenario = {"type": "normal"}

def get_solar_w(step=0):
    if scenario["type"] == "drop":
        return 25.0
    return max(0, irr_values[step % len(irr_values)] * 0.5)

def get_loads():
    return {
        "iron_w":     220,
        "priority_w": 150 if relay_states["priority_health"] else 0,
        "defer_w":    300 if relay_states["defer_residential_a"] else 0,
    }

def update_battery(solar_w, total_w, dt_min=5):
    net_w    = solar_w - total_w
    delta_wh = net_w * (dt_min / 60)
    battery["soc_pct"] = max(0, min(100, battery["soc_pct"] + (delta_wh / battery["capacity_wh"]) * 100))
    battery["voltage_v"] = 11.5 + (battery["soc_pct"] / 100) * 1.2

def set_relay(name, state):
    if name.startswith("iron_"):
        return
    relay_states[name] = state

def snapshot(step=0):
    solar_w = get_solar_w(step)
    loads   = get_loads()
    update_battery(solar_w, sum(loads.values()))
    return {
        "solar_w":      round(solar_w, 1),
        "battery_soc":  round(battery["soc_pct"], 1),
        "battery_v":    round(battery["voltage_v"], 2),
        "iron_w":       loads["iron_w"],
        "priority_w":   loads["priority_w"],
        "defer_w":      loads["defer_w"],
        "relay_states": relay_states.copy(),
        "timestamp":    datetime.now().strftime("%H:%M:%S"),
    }

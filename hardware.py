from datetime import datetime

# ==================================================
# TEMPORARY PLACEHOLDER FUNCTIONS
# Replace these tomorrow with actual sensor readings
# ==================================================

def read_solar():
    return 0.0

def read_battery_soc():
    return 80.0

def read_battery_voltage():
    return 12.5

def read_iron_load():
    return 220

def read_priority_load():
    return 150

def read_defer_load():
    return 300

def read_relay_states():
    return {
        "iron_vaccine": True,
        "iron_water_pump": True,
        "iron_comms": True,
        "priority_health": True,
        "priority_gov": True,
        "defer_residential_a": True,
        "defer_residential_b": True,
        "defer_commercial": True,
    }

# ==================================================
# MAIN SNAPSHOT FUNCTION
# ==================================================

def snapshot(step=0):
    return {
        "solar_w": round(read_solar(), 1),
        "battery_soc": round(read_battery_soc(), 1),
        "battery_v": round(read_battery_voltage(), 2),
        "iron_w": read_iron_load(),
        "priority_w": read_priority_load(),
        "defer_w": read_defer_load(),
        "relay_states": read_relay_states(),
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }

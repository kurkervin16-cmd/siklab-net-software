from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# --- SYSTEM STATE & CONFIGURATION ---
system_state = {
    "sensors": {
        "voltage": 0.0,
        "current": 0.0,
        "power": 0.0,
        "energy": 0.0,
        "frequency": 0.0,
        "pf": 0.0,
        "ldr_digital": 0               # Inverted: 1 = LIGHT (Sensed), 0 = DARK (Clear)
    },
    "relays": [0, 0, 0, 0],               # Exactly 4 Relays: 1 = ON, 0 = OFF
    "mode": "manual",                     # 'manual' or 'auto'
    "rules": {
        "ldr_trigger_enabled": True,      # Enable light-detection rule
        "ldr_relay": 1                    # 1-based index (1 to 4)
    }
}

# --- DASHBOARD HTML/JS TEMPLATE ---
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP32 Smart Controller Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #eceff1; margin: 0; padding: 20px; }
        .container { max-width: 1100px; margin: auto; }
        .card { background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .grid-4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .stat-box { background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #007bff; }
        .stat-box h4 { margin: 0 0 5px 0; color: #6c757d; font-size: 0.85em; text-transform: uppercase; }
        .stat-box p { margin: 0; font-size: 1.4em; font-weight: bold; color: #212529; }
        
        .relay-card { text-align: center; padding: 15px; border-radius: 8px; background: #f8f9fa; border: 1px solid #dee2e6; }
        .btn-relay { width: 100%; padding: 10px 0; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; transition: 0.2s; color: white; margin-top: 8px; font-size: 1.1em; }
        .btn-on { background: #28a745; }
        .btn-off { background: #dc3545; }
        
        .form-group { margin-bottom: 15px; }
        label { display: block; font-weight: bold; margin-bottom: 5px; }
        input[type="number"], select { width: 100%; padding: 8px; border-radius: 5px; border: 1px solid #ccc; box-sizing: border-box; }
        .btn-save { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }
        .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; color: white; font-size: 0.8em; font-weight: bold; }
        .bg-manual { background-color: #ffc107; color: #000; }
        .bg-auto { background-color: #17a2b8; color: white; }
    </style>
</head>
<body>
<div class="container">
    <h2>⚡ ESP32 Hardware & Control Hub</h2>

    <!-- SENSOR TELEMETRY CARD -->
    <div class="card">
        <h3>📊 Live Sensor Telemetry <span id="mode-badge" class="badge"></span></h3>
        <div class="grid-4">
            <div class="stat-box" style="border-color:#4caf50;"><h4>Voltage</h4><p><span id="val-volts">0.0</span> V</p></div>
            <div class="stat-box" style="border-color:#f44336;"><h4>Current</h4><p><span id="val-amps">0.000</span> A</p></div>
            <div class="stat-box" style="border-color:#9c27b0;"><h4>Active Power</h4><p><span id="val-power">0.0</span> W</p></div>
            <div class="stat-box" style="border-color:#3f51b5;"><h4>Energy</h4><p><span id="val-energy">0.000</span> kWh</p></div>
            <div class="stat-box" style="border-color:#009688;"><h4>Power Factor</h4><p><span id="val-pf">0.00</span></p></div>
            <div class="stat-box" style="border-color:#607d8b;"><h4>Light (LDR)</h4><p><span id="val-ldr">DARK</span></p></div>
        </div>
    </div>

    <!-- MANUAL RELAY CONTROL CARD -->
    <div class="card">
        <h3>🔌 Manual Relay Controls (4 Channels)</h3>
        <div class="grid-4" id="relay-container">
            <!-- Dynamically populated via JS -->
        </div>
    </div>

    <!-- AUTOMATION & THRESHOLD INPUT RULES -->
    <div class="card">
        <h3>⚙️ Sensor Automation & Threshold Controls</h3>
        <form id="rules-form">
            <div class="grid-4">
                <div class="form-group">
                    <label>Control Mode</label>
                    <select id="control_mode">
                        <option value="manual">Manual (Web Buttons Override)</option>
                        <option value="auto">Automated (Sensor Threshold Rules)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Light Sense Trigger Relay</label>
                    <select id="ldr_relay"></select>
                </div>
            </div>
            <button type="button" class="btn-save" onclick="saveRules()">Save Automation Rules</button>
        </form>
    </div>
</div>

<script>
    document.addEventListener("DOMContentLoaded", function () {
        const ldrSelect = document.getElementById('ldr_relay');
        for (let i = 1; i <= 4; i++) {
            const opt = document.createElement('option');
            opt.value = i;
            opt.textContent = 'Relay ' + i;
            ldrSelect.appendChild(opt);
        }
        fetchStatus();
        setInterval(fetchStatus, 2000);
    });

    function fetchStatus() {
        fetch('/api/status')
            .then(res => res.json())
            .then(data => {
                document.getElementById('val-volts').innerText = (data.sensors.voltage || 0).toFixed(1);
                document.getElementById('val-amps').innerText = (data.sensors.current || 0).toFixed(3);
                document.getElementById('val-power').innerText = (data.sensors.power || 0).toFixed(1);
                document.getElementById('val-energy').innerText = (data.sensors.energy || 0).toFixed(3);
                document.getElementById('val-pf').innerText = (data.sensors.pf || 0).toFixed(2);
                document.getElementById('val-ldr').innerText = data.sensors.ldr_digital == 1 ? "LIGHT (Sensed)" : "DARK (Clear)";

                const modeBadge = document.getElementById('mode-badge');
                modeBadge.innerText = (data.mode || 'manual').toUpperCase() + " MODE";
                modeBadge.className = 'badge ' + (data.mode === 'auto' ? 'bg-auto' : 'bg-manual');

                let relayHTML = '';
                (data.relays || []).forEach((state, idx) => {
                    const rNum = idx + 1;
                    const isOn = state === 1;
                    relayHTML += '<div class="relay-card">' +
                        '<strong>Relay ' + rNum + '</strong>' +
                        '<p style="margin:5px 0; font-size:0.9em; color:' + (isOn ? '#28a745' : '#dc3545') + '; font-weight:bold;">' +
                            (isOn ? 'ON' : 'OFF') +
                        '</p>' +
                        '<button class="btn-relay ' + (isOn ? 'btn-off' : 'btn-on') + '" onclick="toggleRelay(' + rNum + ', ' + (isOn ? 0 : 1) + ')">' +
                            (isOn ? 'OFF' : 'ON') +
                        '</button>' +
                    '</div>';
                });
                document.getElementById('relay-container').innerHTML = relayHTML;

                if (!window.formInitialized) {
                    document.getElementById('control_mode').value = data.mode;
                    document.getElementById('ldr_relay').value = data.rules.ldr_relay;
                    window.formInitialized = true;
                }
            })
            .catch(err => console.error("Error fetching status:", err));
    }

    function toggleRelay(relayNum, targetState) {
        fetch('/api/relay', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ relay: relayNum, state: targetState })
        }).then(() => fetchStatus());
    }

    function saveRules() {
        const payload = {
            mode: document.getElementById('control_mode').value,
            rules: {
                ldr_relay: parseInt(document.getElementById('ldr_relay').value, 10)
            }
        };
        fetch('/api/settings', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        }).then(() => {
            alert('Settings updated successfully!');
            fetchStatus();
        });
    }
</script>
</body>
</html>"""

# --- ROUTES & ENDPOINTS ---

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data', methods=['POST'], strict_slashes=False)
def receive_sensor_data():
    data = request.get_json(force=True, silent=True)
    
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    # 1. Update Sensor Readings
    pzem = data.get("pzem", {})
    
    system_state["sensors"]["voltage"] = float(pzem.get("voltage", 0.0))
    system_state["sensors"]["current"] = float(pzem.get("current", 0.0))
    system_state["sensors"]["power"] = float(pzem.get("power", 0.0))
    system_state["sensors"]["energy"] = float(pzem.get("energy", 0.0))
    system_state["sensors"]["frequency"] = float(pzem.get("frequency", 0.0))
    system_state["sensors"]["pf"] = float(pzem.get("pf", 0.0))
    system_state["sensors"]["ldr_digital"] = int(data.get("ldr_digital", 0))

    # 2. Automation Logic (If in AUTO Mode)
    if system_state["mode"] == "auto":
        rules = system_state["rules"]
        r_idx = rules.get("ldr_relay", 1) - 1   # Map 1-based index (1-4) to 0-based
        
        if 0 <= r_idx < 4:
            # Reversed: Turn relay ON (1) when light is sensed (ldr_digital == 1)
            system_state["relays"][r_idx] = 1 if system_state["sensors"]["ldr_digital"] == 1 else 0

    # 3. Respond with exact 4-element Relay array to ESP32
    return jsonify({
        "status": "success",
        "relays_command": system_state["relays"]
    }), 200

@app.route('/api/status', methods=['GET'], strict_slashes=False)
def get_status():
    return jsonify(system_state)

@app.route('/api/relay', methods=['POST'], strict_slashes=False)
def manual_relay_toggle():
    data = request.get_json(force=True, silent=True)
    if data and 'relay' in data and 'state' in data:
        r_num = int(data['relay']) # 1-based index (1 to 4)
        if 1 <= r_num <= 4:
            system_state["relays"][r_num - 1] = 1 if data['state'] else 0
            return jsonify({"status": "success", "relays": system_state["relays"]})
    return jsonify({"status": "error", "message": "Invalid relay index"}), 400

@app.route('/api/settings', methods=['POST'], strict_slashes=False)
def update_settings():
    data = request.get_json(force=True, silent=True)
    if data:
        if 'mode' in data:
            system_state["mode"] = data['mode']
        if 'rules' in data:
            system_state["rules"].update(data['rules'])
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

from flask import Flask, request, jsonify
from datetime import datetime
import json
import os

app = Flask(__name__)

# Global memory storage for the latest ESP32 reading
latest_sensor_data = {}

# Optional: Path to log data into your shared FTP directory
SHARED_FTP_DIR = "/srv/ftp/shared"
LOG_FILE = os.path.join(SHARED_FTP_DIR, "latest_sensor_data.json")


# ==========================================================
# ENDPOINT 1: POST /api/data (Receives data from ESP32)
# ==========================================================
@app.route('/api/data', methods=['POST'])
def receive_data():
    global latest_sensor_data
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No JSON payload received"}), 400
       
        # Add server timestamp to the received data
        data['received_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        latest_sensor_data = data
       
        # Log to Pi terminal
        print("\n" + "="*45)
        print(f"[{data['received_at']}] NEW SENSOR DATA RECEIVED")
        print("="*45)
        print(f"  PZEM Meter : {data.get('pzem')}")
        print(f"  DHT11      : {data.get('dht11')}")
        print(f"  LDR Digital: {data.get('ldr_digital')}")
        print(f"  Relay Array: {data.get('relays')}")
        print("="*45)

        # Save latest readings to a JSON file in the shared FTP directory
        if os.path.exists(SHARED_FTP_DIR):
            with open(LOG_FILE, 'w') as f:
                json.dump(data, f, indent=4)

        return jsonify({"status": "success", "message": "Data received successfully"}), 200

    except Exception as e:
        print(f"[ERROR] Exception processing request: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ==========================================================
# ENDPOINT 2: GET /api/latest (Fetch latest sensor readings)
# ==========================================================
@app.route('/api/latest', methods=['GET'])
def get_latest_data():
    if not latest_sensor_data:
        return jsonify({"status": "empty", "message": "No telemetry data recorded yet."}), 404
   
    return jsonify({
        "status": "success",
        "data": latest_sensor_data
    }), 200


# ==========================================================
# ENDPOINT 3: GET /api/status (Health check endpoint)
# ==========================================================
@app.route('/api/status', methods=['GET'])
def server_status():
    return jsonify({
        "status": "online",
        "server": "Raspberry Pi IoT Telemetry Gateway",
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }), 200


if __name__ == '__main__':
    # host='0.0.0.0' enables incoming network requests on port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
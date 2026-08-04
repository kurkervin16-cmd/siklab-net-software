import serial
import time
import threading
import sys
import queue

# ==================================================
# CONFIGURATION
# ==================================================
SERIAL_PORT = "/dev/serial0"  # Default Pi hardware UART
BAUD_RATE = 9600

PHONE_NUMBER = "+639163524888"
MESSAGE = "kurk abno."

# Global objects
ser = None
running = True
serial_lock = threading.Lock()
input_queue = queue.Queue()

# ==================================================
# AT COMMAND & SMS FUNCTIONS
# ==================================================

def send_command(command, timeout=2.0):
    """Sends a standard AT command and prints/returns the response."""
    with serial_lock:
        print(f">> {command}")
        # Clear out any residual serial garbage before sending
        ser.reset_input_buffer()
        
        # Standard AT commands end with \r\n
        ser.write((command + "\r\n").encode('utf-8'))
        ser.flush()
        
        start_time = time.time()
        response = ""
        while (time.time() - start_time) < timeout:
            if ser.in_waiting > 0:
                chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                response += chunk
                sys.stdout.write(chunk)
                sys.stdout.flush()
            time.sleep(0.05)
        print()
        return response


def send_sms(number, msg):
    """Sends an SMS by strictly using '\r' for AT+CMGS and locking thread reads."""
    print("\n--- Sending SMS ---")
    
    with serial_lock:
        # Step 1: Purge the RX buffer completely
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.1)
        
        # Step 2: Send AT+CMGS command with ONLY \r (Carriage Return)
        # Adding \n here breaks the modem's prompt mechanism!
        cmgs_cmd = f'AT+CMGS="{number}"\r'
        ser.write(cmgs_cmd.encode('utf-8'))
        ser.flush()

        # Step 3: Wait for the '>' prompt
        start_time = time.time()
        prompt_received = False
        raw_rx = ""
        
        while (time.time() - start_time) < 6.0:
            if ser.in_waiting > 0:
                char = ser.read(1).decode('utf-8', errors='ignore')
                raw_rx += char
                sys.stdout.write(char)
                sys.stdout.flush()
                
                if '>' in char:
                    prompt_received = True
                    break
            time.sleep(0.01)

        # Handle failure to receive prompt
        if not prompt_received:
            print("\nERROR: No '>' prompt received from SIM800L.")
            # Send ESC key (ASCII 27 / 0x1B) to exit CMGS mode safely
            ser.write(b'\x1b')
            ser.flush()
            time.sleep(0.5)
            ser.reset_input_buffer()
            return False

        # Step 4: Write message body followed by Ctrl+Z (ASCII 26 / 0x1A)
        # Delay briefly to let the modem settle into prompt mode
        time.sleep(0.2)
        payload = msg + chr(26)
        ser.write(payload.encode('utf-8'))
        ser.flush()
        
        print("\nPayload sent. Waiting for network confirmation...")
        
        # Step 5: Wait for OK or +CMGS response from the network
        start_time = time.time()
        response = ""
        while (time.time() - start_time) < 15.0:
            if ser.in_waiting > 0:
                chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                response += chunk
                sys.stdout.write(chunk)
                sys.stdout.flush()
                
                if "OK" in response or "+CMGS:" in response:
                    print("\n*** SMS SENT SUCCESSFULLY ***\n")
                    return True
                if "ERROR" in response or "+CMS ERROR" in response:
                    print("\n*** SMS FAILED ***\n")
                    return False
            time.sleep(0.05)
            
        print("\n*** SMS RESPONSE TIMEOUT ***\n")
        return False

# ==================================================
# THREAD WORKERS
# ==================================================

def sim800_listener():
    """Background listener for incoming notifications when serial_lock is available."""
    global running

    while running:
        # Non-blocking lock acquire ensures listener won't steal bytes during send_sms()
        acquired = serial_lock.acquire(blocking=False)
        if acquired:
            try:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        if "RING" in line or "+CLIP:" in line:
                            print("\n>>> INCOMING CALL DETECTED! REJECTING... <<<")
                            ser.write(b"ATH\r\n")
                            ser.flush()
                        elif "+CMT:" in line:
                            print(f"\n[INCOMING SMS HEADER]: {line}")
                            # Read the message body from the next line
                            time.sleep(0.1)
                            if ser.in_waiting > 0:
                                body = ser.readline().decode('utf-8', errors='ignore').strip()
                                print(f"[INCOMING SMS BODY]  : {body}\n")
                        else:
                            print(f"[SIM800]: {line}")
            finally:
                serial_lock.release()

        time.sleep(0.05)


def terminal_reader():
    """Captures manual terminal commands without blocking execution."""
    while running:
        try:
            line = sys.stdin.readline()
            if line:
                input_queue.put(line.strip())
        except Exception:
            break

# ==================================================
# MAIN ENTRY POINT
# ==================================================

def main():
    global ser, running

    try:
        ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUD_RATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        time.sleep(1)
    except serial.SerialException as e:
        print(f"Failed to open serial port {SERIAL_PORT}: {e}")
        sys.exit(1)

    print("\n==============================")
    print(" Raspberry Pi + SIM800L Ready ")
    print("==============================")

    # Clean serial buffers on boot
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # [1] Initial Setup AT Commands
    print("\n[1] Initializing SIM800L...")
    send_command("AT")
    send_command("ATE0")               # Disable echo
    send_command("AT+CPIN?")           # Verify SIM state
    send_command("AT+CSQ")             # Check signal
    send_command("AT+CREG?")           # Check network registration
    send_command("AT+CMGF=1")          # Enable Text Mode
    send_command('AT+CSCS="GSM"')      # Set GSM character set

    # [2] Configure Call & SMS Behavior
    print("\n[2] Setting Call & Receiving Rules...")
    send_command("AT+CLIP=1")          # Enable caller ID
    send_command("AT+CNMI=2,2,0,0,0")  # Directly output SMS payload to serial

    # [3] Initial Startup SMS Test
    print("\n[3] Sending initial test SMS...")
    send_sms(PHONE_NUMBER, MESSAGE)

    # [4] Spin up Background Listener & Input Threads
    threading.Thread(target=sim800_listener, daemon=True).start()
    threading.Thread(target=terminal_reader, daemon=True).start()

    print("\n==============================")
    print(" Listening for Incoming Calls & SMS...")
    print(" Type 'SEND' in terminal to trigger SMS.")
    print(" Press Ctrl+C to exit.")
    print("==============================\n")

    # [5] Event Loop
    try:
        while True:
            if not input_queue.empty():
                cmd = input_queue.get()
                if cmd.upper() == "SEND":
                    send_sms(PHONE_NUMBER, MESSAGE)
                elif cmd:
                    send_command(cmd)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nExiting program...")
        running = False
        if ser and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()

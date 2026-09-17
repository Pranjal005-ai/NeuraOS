"""
serial_controller.py

Handles communication between the Raspberry Pi
and the ESP32.

Currently runs in SIMULATED mode if pyserial
or an ESP32 is not available.
"""

try:
    import serial

    SERIAL_AVAILABLE = True

except ImportError:

    SERIAL_AVAILABLE = False

    print("⚠️ pyserial not installed. Running in SIMULATED mode.")


PORT = "/dev/cu.usbserial-0001"      # Raspberry Pi default
BAUDRATE = 115200

_simulated = True
_connection = None


def connect():

    global _connection
    global _simulated

    if not SERIAL_AVAILABLE:

        return False

    try:

        _connection = serial.Serial(
            PORT,
            BAUDRATE,
            timeout=1
        )

        _simulated = False

        print(f"✅ Connected to ESP32 on {PORT}")

        return True

    except Exception as e:

        print(f"⚠️ ESP32 not connected ({e})")
        print("Running in SIMULATED mode.")

        _simulated = True

        return False


def send(command):

    if _simulated:

        print(f"📤 SIMULATED -> {command}")

        return

    _connection.write(
        f"{command}\n".encode()
    )


def receive():

    if _simulated:

        return None

    if _connection.in_waiting:

        return (
            _connection.readline()
            .decode()
            .strip()
        )

    return None


def disconnect():

    global _connection

    if _connection:

        _connection.close()

        print("ESP32 disconnected.")
"""
=========================================================
esp32/esp32.py

Serial link between the Pi (or Mac) and the ESP32.

Author: Pranjal

Run from the PROJECT ROOT:
    python3 -m esp32.esp32          # detect and report

WHY THE CONSTRUCTOR NO LONGER RAISES
------------------------------------
`esp32 = ESP32()` runs at import, and the old constructor
opened the serial port there. So on a machine with no
ESP32 attached -- your Mac, every time -- importing
assistant.py died with a SerialException, taking down
the entire import chain with it.

Same failure as the camera: opening hardware as a side
effect of an import makes every module that transitively
imports it undeployable anywhere the hardware is absent.

Now a missing ESP32 is a NORMAL, LOGGED condition.
send() returns False, read() returns None, and the rest
of NeuraOS runs.

PORT AUTO-DETECTION
-------------------
The hardcoded /dev/cu.usbserial-0001 is a macOS path
that will not exist on the Pi (/dev/ttyUSB0 or
/dev/ttyACM0), and changes between adapters even on the
same Mac. Ports are now probed in order.

RECONNECTION
------------
A briefly unplugged cable used to require restarting the
whole robot. The link now retries in the background, on
a backoff, so it recovers on its own.
=========================================================
"""

import glob
import json
import platform
import threading
import time

try:
    import serial
    from serial.tools import list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


BAUDRATE = 115200

# Don't hammer a missing port -- back off between tries.
RECONNECT_MIN = 2.0
RECONNECT_MAX = 30.0

# USB-serial chips commonly used on ESP32 dev boards.
KNOWN_CHIPS = ("CP210", "CH340", "CH910", "FTDI", "FT232", "Silicon Labs")


####################################################
# Finding the board
####################################################

def candidate_ports():
    """
    Likely ESP32 serial ports, best guess first.
    """

    found = []

    ################################################
    # Ask pyserial first -- it knows the chip names
    ################################################

    if SERIAL_AVAILABLE:

        try:
            for port in list_ports.comports():

                description = (
                    f"{port.description} {port.manufacturer}"
                )

                if any(chip.lower() in description.lower()
                       for chip in KNOWN_CHIPS):
                    found.append(port.device)

        except Exception:
            pass

    ################################################
    # Fall back to globbing the usual paths
    ################################################

    system = platform.system()

    if system == "Darwin":
        patterns = [
            "/dev/cu.usbserial*",
            "/dev/cu.SLAB_USBtoUART*",
            "/dev/cu.wchusbserial*",
        ]

    elif system == "Linux":
        # Pi: ttyUSB0 for CP210x/CH340, ttyACM0 for
        # native-USB boards.
        patterns = [
            "/dev/ttyUSB*",
            "/dev/ttyACM*",
        ]

    else:
        patterns = []

    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            if path not in found:
                found.append(path)

    return found


class ESP32:

    def __init__(self, port=None, baudrate=BAUDRATE, auto_reconnect=True):

        self.requested_port = port
        self.baudrate = baudrate

        self.serial = None
        self.port = None

        self._lock = threading.Lock()

        self._last_attempt = 0.0
        self._backoff = RECONNECT_MIN

        self.auto_reconnect = auto_reconnect

        self.connect()

    ####################################################

    def connect(self):
        """
        Try to open the link. Never raises.

        Returns True if connected.
        """

        if not SERIAL_AVAILABLE:

            # Warn once, not on every reconnect attempt --
            # otherwise a machine without pyserial fills
            # the log with the same line forever.
            if not getattr(ESP32, "_warned_no_serial", False):
                print("[ESP32] pyserial not installed -- link disabled")
                ESP32._warned_no_serial = True

            self.auto_reconnect = False

            return False

        ports = (
            [self.requested_port] if self.requested_port
            else candidate_ports()
        )

        if not ports:
            print("[ESP32] No serial ports found")
            return False

        for port in ports:

            try:
                self.serial = serial.Serial(
                    port,
                    self.baudrate,
                    timeout=1
                )

                self.port = port

                self._backoff = RECONNECT_MIN

                # Boards reset when the port opens; give
                # the bootloader a moment before trusting
                # anything we read.
                time.sleep(0.3)

                self.serial.reset_input_buffer()

                print(f"[ESP32] Connected on {port}")

                return True

            except Exception as exc:
                # Expected on a dev machine with no board.
                last_error = exc
                continue

        print(
            f"[ESP32] Not connected "
            f"(tried {len(ports)} port(s)) -- running without it"
        )

        return False

    ####################################################

    def connected(self):

        return self.serial is not None and self.serial.is_open

    ####################################################

    def _maybe_reconnect(self):
        """
        Retry on a backoff, so a briefly unplugged cable
        recovers without restarting the robot -- and a
        permanently absent board doesn't spam the log.
        """

        if not self.auto_reconnect or self.connected():
            return

        now = time.time()

        if now - self._last_attempt < self._backoff:
            return

        self._last_attempt = now

        if not self.connect():
            self._backoff = min(self._backoff * 2, RECONNECT_MAX)

    ####################################################

    def _drop(self, reason):

        print(f"[ESP32] Link lost: {reason}")

        try:
            if self.serial:
                self.serial.close()
        except Exception:
            pass

        self.serial = None

    ####################################################

    def send(self, command):
        """
        Send a line. Returns True if it went out.

        Returns False rather than raising when there is
        no board -- callers should be able to run without
        one.
        """

        self._maybe_reconnect()

        if not self.connected():
            return False

        with self._lock:

            try:
                self.serial.write((command + "\n").encode())
                self.serial.flush()

                return True

            except Exception as exc:
                self._drop(str(exc))
                return False

    ####################################################

    def send_json(self, payload):

        try:
            return self.send(json.dumps(payload))
        except Exception:
            return False

    ####################################################

    def read(self):
        """
        One waiting line, parsed as JSON if possible.

        Returns None when nothing is waiting OR when
        there is no board. Callers already treat None as
        "no data", so absence degrades cleanly.
        """

        self._maybe_reconnect()

        if not self.connected():
            return None

        with self._lock:

            try:
                if not self.serial.in_waiting:
                    return None

                raw = self.serial.readline()

            except Exception as exc:
                self._drop(str(exc))
                return None

        try:
            line = raw.decode("utf-8", errors="replace").strip()
        except Exception:
            return None

        if not line:
            return None

        try:
            return json.loads(line)
        except Exception:
            # Plain text -- boot messages, debug prints.
            return line

    ####################################################

    def read_latest(self, limit=20):
        """
        Drain the buffer and return the NEWEST reading.

        Sensor data arrives faster than the control loop
        consumes it, so read() alone returns increasingly
        stale values while the backlog grows. For
        obstacle distances, stale is worse than nothing.
        """

        latest = None

        for _ in range(limit):

            value = self.read()

            if value is None:
                break

            latest = value

        return latest

    ####################################################

    def close(self):

        with self._lock:

            try:
                if self.serial:
                    self.serial.close()
            except Exception:
                pass

            self.serial = None


####################################################
# Singleton
#
# Still constructed at import, because everything else
# expects `from .esp32 import esp32` -- but now it
# cannot take the process down.
####################################################

esp32 = ESP32()


####################################################

if __name__ == "__main__":

    print("=" * 52)
    print("VED  --  ESP32 LINK")
    print("=" * 52)

    print(f"\npyserial installed : {SERIAL_AVAILABLE}")

    ports = candidate_ports()

    print(f"Candidate ports    : {ports or 'none found'}")

    link = ESP32()

    print(f"Connected          : {link.connected()}")

    if not link.connected():
        print(
            "\nNo board attached. This is fine on the dev"
            "\nmachine -- send() returns False, read()"
            "\nreturns None, and nothing crashes."
        )

        print(f"\n  send('PING') -> {link.send('PING')}")
        print(f"  read()       -> {link.read()}")

    else:
        print(f"Port               : {link.port}")

        print("\nListening for 5s...\n")

        end = time.time() + 5

        while time.time() < end:

            data = link.read()

            if data is not None:
                print(f"  {data}")

            time.sleep(0.05)

        link.close()
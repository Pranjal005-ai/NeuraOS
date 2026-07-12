"""
motor_controller.py
Drives the 4 BO motors via the L298N driver.

Works in two modes:
- REAL mode: on the Raspberry Pi, where RPi.GPIO is available.
- SIMULATED mode: on a dev machine (Mac/Windows/Linux without RPi.GPIO),
  where every call just prints what it *would* do. This lets the full
  voice -> decision -> "movement" flow be tested before the code is
  ever copied onto the Pi.
"""

try:
    import RPi.GPIO as GPIO
    SIMULATED = False

except ImportError:
    SIMULATED = True
    print("⚠️ RPi.GPIO not found — motor_controller running in SIMULATED mode.")
    print("   (This is expected on a Mac/PC. Real GPIO will be used on the Pi.)")

# GPIO Pin Numbers
LEFT_MOTOR_IN1 = 12
LEFT_MOTOR_IN2 = 16
RIGHT_MOTOR_IN1 = 20
RIGHT_MOTOR_IN2 = 21

if not SIMULATED:

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    GPIO.setup(LEFT_MOTOR_IN1, GPIO.OUT)
    GPIO.setup(LEFT_MOTOR_IN2, GPIO.OUT)
    GPIO.setup(RIGHT_MOTOR_IN1, GPIO.OUT)
    GPIO.setup(RIGHT_MOTOR_IN2, GPIO.OUT)


def _set_pins(left_in1, left_in2, right_in1, right_in2):
    """
    Sets the 4 motor pins, or prints the equivalent action if
    running in SIMULATED mode.
    """

    if SIMULATED:
        return

    GPIO.output(LEFT_MOTOR_IN1, left_in1)
    GPIO.output(LEFT_MOTOR_IN2, left_in2)
    GPIO.output(RIGHT_MOTOR_IN1, right_in1)
    GPIO.output(RIGHT_MOTOR_IN2, right_in2)


def forward():

    print("🟢 [MOTOR] Forward")

    _set_pins(False, True, False, True)


def backward():

    print("🟢 [MOTOR] Backward")

    _set_pins(True, False, True, False)


def left():

    print("🟢 [MOTOR] Turning Left")

    _set_pins(False, True, True, False)


def right():

    print("🟢 [MOTOR] Turning Right")

    _set_pins(True, False, False, True)


def stop():

    print("🟢 [MOTOR] Stop")

    _set_pins(False, False, False, False)


def cleanup():

    stop()

    if not SIMULATED:
        GPIO.cleanup()
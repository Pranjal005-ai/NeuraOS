"""
motor_controller.py

High-level motor API for Ved.

This module hides whether motors are driven
through Raspberry Pi GPIO or an ESP32.
"""

from motion.serial_controller import (
    connect,
    send,
)

try:

    import RPi.GPIO as GPIO

    GPIO_AVAILABLE = True

except ImportError:

    GPIO_AVAILABLE = False


ESP32_CONNECTED = connect()


# ---------------------------------
# Raspberry Pi GPIO Pins
# ---------------------------------

LEFT_MOTOR_IN1 = 12
LEFT_MOTOR_IN2 = 16

RIGHT_MOTOR_IN1 = 20
RIGHT_MOTOR_IN2 = 21


if GPIO_AVAILABLE:

    GPIO.setmode(GPIO.BCM)

    GPIO.setwarnings(False)

    GPIO.setup(LEFT_MOTOR_IN1, GPIO.OUT)
    GPIO.setup(LEFT_MOTOR_IN2, GPIO.OUT)
    GPIO.setup(RIGHT_MOTOR_IN1, GPIO.OUT)
    GPIO.setup(RIGHT_MOTOR_IN2, GPIO.OUT)


def gpio_drive(l1, l2, r1, r2):

    if not GPIO_AVAILABLE:
        return

    GPIO.output(LEFT_MOTOR_IN1, l1)
    GPIO.output(LEFT_MOTOR_IN2, l2)

    GPIO.output(RIGHT_MOTOR_IN1, r1)
    GPIO.output(RIGHT_MOTOR_IN2, r2)


# ==========================================
# High-Level Motion API
# ==========================================

def forward():

    print("🟢 Forward")

    send("MOVE_FORWARD")

    gpio_drive(False, True, False, True)


def backward():

    print("🟢 Backward")

    send("MOVE_BACKWARD")

    gpio_drive(True, False, True, False)


def left():

    print("🟢 Turn Left")

    send("TURN_LEFT")

    gpio_drive(False, True, True, False)


def right():

    print("🟢 Turn Right")

    send("TURN_RIGHT")

    gpio_drive(True, False, False, True)


def stop():

    print("🟢 Stop")

    send("STOP")

    gpio_drive(False, False, False, False)


def cleanup():

    stop()

    if GPIO_AVAILABLE:

        GPIO.cleanup()
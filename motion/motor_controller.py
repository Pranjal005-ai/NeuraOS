import RPi.GPIO as GPIO
import time

# GPIO Pin Numbers
LEFT_MOTOR_IN1 = 12
LEFT_MOTOR_IN2 = 16
RIGHT_MOTOR_IN1 = 20
RIGHT_MOTOR_IN2 = 21

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(LEFT_MOTOR_IN1, GPIO.OUT)
GPIO.setup(LEFT_MOTOR_IN2, GPIO.OUT)
GPIO.setup(RIGHT_MOTOR_IN1, GPIO.OUT)
GPIO.setup(RIGHT_MOTOR_IN2, GPIO.OUT)


def forward():
    GPIO.output(LEFT_MOTOR_IN1, False)
    GPIO.output(LEFT_MOTOR_IN2, True)
    GPIO.output(RIGHT_MOTOR_IN1, False)
    GPIO.output(RIGHT_MOTOR_IN2, True)


def backward():
    GPIO.output(LEFT_MOTOR_IN1, True)
    GPIO.output(LEFT_MOTOR_IN2, False)
    GPIO.output(RIGHT_MOTOR_IN1, True)
    GPIO.output(RIGHT_MOTOR_IN2, False)


def left():
    GPIO.output(LEFT_MOTOR_IN1, False)
    GPIO.output(LEFT_MOTOR_IN2, True)
    GPIO.output(RIGHT_MOTOR_IN1, True)
    GPIO.output(RIGHT_MOTOR_IN2, False)


def right():
    GPIO.output(LEFT_MOTOR_IN1, True)
    GPIO.output(LEFT_MOTOR_IN2, False)
    GPIO.output(RIGHT_MOTOR_IN1, False)
    GPIO.output(RIGHT_MOTOR_IN2, True)


def stop():
    GPIO.output(LEFT_MOTOR_IN1, False)
    GPIO.output(LEFT_MOTOR_IN2, False)
    GPIO.output(RIGHT_MOTOR_IN1, False)
    GPIO.output(RIGHT_MOTOR_IN2, False)


def cleanup():
    stop()
    GPIO.cleanup()  
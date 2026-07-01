import RPi.GPIO as GPIO
from config import *

class GPIOManager:

    def __init__(self):

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

    def setup(self):

        GPIO.setup(LEFT_MOTOR_FORWARD, GPIO.OUT)
        GPIO.setup(LEFT_MOTOR_BACKWARD, GPIO.OUT)

        GPIO.setup(RIGHT_MOTOR_FORWARD, GPIO.OUT)
        GPIO.setup(RIGHT_MOTOR_BACKWARD, GPIO.OUT)

    def cleanup(self):

        GPIO.cleanup()
from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ROBOT_NAME = os.getenv("ROBOT_NAME", "Ved")
DEBUG = os.getenv("DEBUG", "True")

LISTEN_TIMEOUT = 5

VOICE = "alloy"

CAMERA_ENABLED = True

MOTOR_ENABLED = True
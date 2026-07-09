"""
speaker.py
OpenAI Text-to-Speech for Ved
"""

import os
import tempfile

import pygame
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

pygame.mixer.init()


def speak(text):

    if not text:
        return

    text = str(text)

    print("🔊 Speaking:", text)

    try:

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".mp3"
        ) as temp_audio:

            response = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="alloy",
                input=text
            )

            response.stream_to_file(temp_audio.name)

            print("✅ Audio file created")

            pygame.mixer.music.load(temp_audio.name)
            print("✅ Audio loaded")
            pygame.mixer.music.play()
            print("▶ Playing...")

            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

        os.remove(temp_audio.name)

    except Exception as e:
        print("Speaker Error:", e)
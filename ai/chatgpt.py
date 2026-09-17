"""
chatgpt.py
Author: Pranjal

Handles OpenAI communication.
"""

from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()


client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def ask_ai(prompt, session=None):
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content
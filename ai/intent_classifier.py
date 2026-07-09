from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def classify(command):

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": """
Return ONLY one of these intents:

CHAT
MOVE_FORWARD
MOVE_BACKWARD
TURN_LEFT
TURN_RIGHT
STOP
MEMORY_SAVE
MEMORY_READ

Do not explain.
Return only the intent.
"""
            },
            {
                "role": "user",
                "content": command
            }
        ]
    )

    return response.choices[0].message.content.strip()
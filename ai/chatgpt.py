from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def ask_ai(prompt):

    response = client.chat.completions.create(

        model="gpt-4.1-mini",

        messages=[
            {
                "role": "system",
                "content": """
You are an intelligent home robot.

Keep replies short.

Understand movement commands.

Examples:

Go forward
Go backward
Turn left
Turn right
Stop

If the user asks general questions, answer normally.
"""
            },

            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content
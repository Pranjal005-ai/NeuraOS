from openai import OpenAI
from config import OPENAI_API_KEY
from personality.personality import VED_PERSONALITY

client = OpenAI(api_key=OPENAI_API_KEY)

def ask_ai(prompt, session):

    messages = [
        {
            "role": "system",
            "content": VED_PERSONALITY
        }
    ]

    # Add previous conversation
    messages.extend(session.get_history())

    # Add current user message
    messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages
    )

    reply = response.choices[0].message.content

    # Save conversation
    session.add_message("user", prompt)
    session.add_message("assistant", reply)

    return reply
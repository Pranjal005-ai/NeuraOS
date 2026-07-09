import speech_recognition as sr

recognizer = sr.Recognizer()

recognizer.dynamic_energy_threshold = False
recognizer.energy_threshold = 300
recognizer.pause_threshold = 1.2


def listen():

    with sr.Microphone(device_index=2) as source:

        print("🎤 Speak now...")

        audio = recognizer.listen(
            source,
            timeout=20,
            phrase_time_limit=10
        )

    print("✅ Audio captured")

    try:
        text = recognizer.recognize_google(audio, language="hi-IN")

        print("You said:", text)

        return text.lower()

    except Exception as e:

        print("Recognition Error:", repr(e))

        return ""
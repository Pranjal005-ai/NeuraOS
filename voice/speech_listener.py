import speech_recognition as sr

recognizer = sr.Recognizer()

# Speech Recognition Settings
recognizer.dynamic_energy_threshold = False
recognizer.energy_threshold = 300
recognizer.pause_threshold = 1.2

# Manual override (optional)
# Set to an integer like 2 if you ever want to force a specific microphone.
MIC_DEVICE_INDEX = None

# Keywords used to auto-detect a USB microphone.
USB_MIC_NAME_HINTS = [
    "usb",
    "microphone",
    "mic",
    "headset"
]


def find_mic_index():
    """
    Automatically finds a suitable microphone by name.
    This avoids hardcoding device indices, which can change
    across different computers or Raspberry Pi.
    """

    if MIC_DEVICE_INDEX is not None:
        return MIC_DEVICE_INDEX

    mic_names = sr.Microphone.list_microphone_names()

    print("\nAvailable Microphones:")

    for index, name in enumerate(mic_names):

        print(f"{index}: {name}")

        if any(hint in name.lower() for hint in USB_MIC_NAME_HINTS):

            print(f"\n🎙️ Using microphone [{index}] : {name}")

            return index

    print("\n⚠️ USB microphone not found.")
    print("Using system default microphone.\n")

    return None


def listen():

    mic_index = find_mic_index()

    with sr.Microphone(device_index=mic_index) as source:

        print("🎤 Calibrating microphone...")

        recognizer.adjust_for_ambient_noise(
            source,
            duration=1
        )

        print("🎤 Speak now...")

        audio = recognizer.listen(
            source,
            timeout=20,
            phrase_time_limit=10
        )

    print("✅ Audio captured")

    try:

        text = recognizer.recognize_google(
            audio,
            language="hi-IN"
        )

        print("🗣️ You said:", text)

        return text.lower()

    except sr.UnknownValueError:

        print("❌ Could not understand audio")

        return ""

    except sr.RequestError as e:

        print("❌ Google Speech Recognition error:", e)

        return ""

    except Exception as e:

        print("❌ Recognition Error:", repr(e))

        return ""
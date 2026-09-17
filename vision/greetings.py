"""
=========================================================
greetings.py

Everything Ved says, in every language it says it in.

Author: Pranjal

WHY HINGLISH IS A SEPARATE LANGUAGE
-----------------------------------
Two reasons, one social and one technical.

SOCIAL: almost nobody under 30 in an Indian city speaks
pure Hindi conversationally. "आपसे मिलकर अच्छा लगा" is
correct and nobody says it. "Aapse milkar accha laga,
nice to meet you!" is what people actually sound like.
A robot that speaks textbook Hindi reads as stiff --
which is worse than reading as foreign.

TECHNICAL: Hinglish is written in Roman script, so a
standard English TTS voice can speak it. Pronunciation
is imperfect but recognisable. Devanagari needs an
Indic-capable voice (Piper with a Hindi model, Coqui, or
cloud TTS) which is a much bigger dependency on a Pi.

So Hinglish works TODAY with whatever TTS you have, and
Hindi waits until the voice stack is sorted. For an
Indian hospitality deployment, Hinglish is arguably the
better default anyway.

TRANSLATION CAVEAT
------------------
The Devanagari lines are my best effort, not a native
speaker's. Get someone local to read them before a
client demo -- especially the Rajasthani, which varies
a lot by region.
=========================================================
"""


DEFAULT_LANGUAGE = "English"

# Consider switching this to "Hinglish" for an Indian
# deployment -- it is the safest opener with a stranger
# whose language you don't know yet, and it needs no
# special TTS voice.
GREETING_STRANGER_LANGUAGE = "English"


####################################################
# What people might say when asked their language
####################################################

LANGUAGE_ALIASES = {
    "english": "English",
    "angrezi": "English",
    "इंग्लिश": "English",
    "अंग्रेजी": "English",

    # Check Hinglish BEFORE Hindi -- "hindi english"
    # contains "hindi" and would otherwise match wrong.
    "hinglish": "Hinglish",
    "hindi english": "Hinglish",
    "hindi and english": "Hinglish",
    "mix": "Hinglish",
    "mixed": "Hinglish",
    "both": "Hinglish",
    "dono": "Hinglish",
    "casual": "Hinglish",

    "hindi": "Hindi",
    "हिंदी": "Hindi",
    "हिन्दी": "Hindi",
    "shuddh hindi": "Hindi",
    "pure hindi": "Hindi",

    "marathi": "Marathi",
    "मराठी": "Marathi",

    "gujarati": "Gujarati",
    "gujrati": "Gujarati",
    "ગુજરાતી": "Gujarati",

    "rajasthani": "Rajasthani",
    "marwari": "Rajasthani",
    "mewari": "Rajasthani",
    "मारवाड़ी": "Rajasthani",
    "राजस्थानी": "Rajasthani",
}

# Longest aliases first, so "hindi english" wins over
# "hindi" and "pure hindi" wins over "hinglish".
_ALIAS_ORDER = sorted(
    LANGUAGE_ALIASES.items(),
    key=lambda item: len(item[0]),
    reverse=True
)


def parse_language(text):
    """
    Map a spoken reply to a supported language, or None.
    """

    if not text:
        return None

    lowered = text.strip().lower()

    for alias, language in _ALIAS_ORDER:
        if alias in lowered:
            return language

    return None


####################################################
# Phrase bank
#
# {name} is substituted at call time.
####################################################

PHRASES = {

    ################################################
    # Meeting someone new
    ################################################

    "ask_name": {
        "English": "I don't think we've met. What's your name?",
        "Hinglish": "Hey! Hum pehle mile nahi hain na. Aapka naam kya hai?",
        "Hindi": "लगता है हम पहले नहीं मिले। आपका नाम क्या है?",
        "Marathi": "आपली भेट झाली नाही असं वाटतं. आपलं नाव काय?",
        "Gujarati": "લાગે છે આપણે પહેલાં મળ્યા નથી. તમારું નામ શું છે?",
        "Rajasthani": "म्हांरो ख्याल है आपां पैली नीं मिल्या। थांरो नाम कांई है?",
    },

    "ask_language": {
        "English": "Which language should I speak with you?",
        "Hinglish": "Main aapse kis language mein baat karun?",
        "Hindi": "मैं आपसे किस भाषा में बात करूँ?",
        "Marathi": "मी आपल्याशी कोणत्या भाषेत बोलू?",
        "Gujarati": "હું તમારી સાથે કઈ ભાષામાં વાત કરું?",
        "Rajasthani": "म्हूं थांसूं कुण सी भाषा में बात करूं?",
    },

    "hold_still": {
        "English": "Nice to meet you, {name}. Hold still for a moment.",
        "Hinglish": "Nice to meet you, {name}! Bas ek second still rahiye.",
        "Hindi": "आपसे मिलकर अच्छा लगा, {name}। एक पल स्थिर रहिए।",
        "Marathi": "भेटून आनंद झाला, {name}. क्षणभर स्थिर रहा.",
        "Gujarati": "તમને મળીને આનંદ થયો, {name}. એક ક્ષણ સ્થિર રહો.",
        "Rajasthani": "थांसूं मिलर घणो चोखो लाग्यो, {name}। एक पल थिर रैवो।",
    },

    "look_at_me": {
        "English": "Look at me please.",
        "Hinglish": "Mere taraf dekhiye please.",
        "Hindi": "कृपया मेरी तरफ देखिए।",
        "Marathi": "कृपया माझ्याकडे बघा.",
        "Gujarati": "કૃપા કરીને મારી તરફ જુઓ.",
        "Rajasthani": "किरपा कर म्हांरी कानी देखो।",
    },

    "turn_left": {
        "English": "Now turn your head slightly to the left.",
        "Hinglish": "Ab thoda left side turn kijiye.",
        "Hindi": "अब सिर थोड़ा बाईं ओर घुमाइए।",
        "Marathi": "आता डोकं थोडं डावीकडे वळवा.",
        "Gujarati": "હવે માથું થોડું ડાબી બાજુ ફેરવો.",
        "Rajasthani": "अब माथो थोड़ो डाबी कानी घुमावो।",
    },

    "turn_right": {
        "English": "And to the right.",
        "Hinglish": "Aur ab right side.",
        "Hindi": "और अब दाईं ओर।",
        "Marathi": "आणि आता उजवीकडे.",
        "Gujarati": "અને હવે જમણી બાજુ.",
        "Rajasthani": "अर अब जीमणी कानी।",
    },

    "enrolled": {
        "English": "Got it. I'll remember you, {name}.",
        "Hinglish": "Done! Ab main aapko yaad rakhunga, {name}.",
        "Hindi": "हो गया। मैं आपको याद रखूँगा, {name}।",
        "Marathi": "झालं. मी तुम्हाला लक्षात ठेवीन, {name}.",
        "Gujarati": "થઈ ગયું. હું તમને યાદ રાખીશ, {name}.",
        "Rajasthani": "हो गयो। म्हूं थांने याद राखूंलो, {name}।",
    },

    ################################################
    # Greeting someone known
    ################################################

    "greet_first": {
        "English": "Hello {name}. Nice to meet you.",
        "Hinglish": "Hello {name}! Aapse milkar accha laga.",
        "Hindi": "नमस्ते {name}। आपसे मिलकर अच्छा लगा।",
        "Marathi": "नमस्कार {name}. भेटून आनंद झाला.",
        "Gujarati": "નમસ્તે {name}. તમને મળીને આનંદ થયો.",
        "Rajasthani": "राम राम सा {name}। थांसूं मिलर घणो चोखो लाग्यो।",
    },

    "greet_back_soon": {
        "English": "You're back, {name}.",
        "Hinglish": "Arre {name}, wapas aa gaye!",
        "Hindi": "आप वापस आ गए, {name}।",
        "Marathi": "तुम्ही परत आलात, {name}.",
        "Gujarati": "તમે પાછા આવ્યા, {name}.",
        "Rajasthani": "थे पाछा आय ग्या, {name}।",
    },

    "greet_again": {
        "English": "Hello again, {name}.",
        "Hinglish": "Hello again, {name}!",
        "Hindi": "फिर से नमस्ते, {name}।",
        "Marathi": "पुन्हा नमस्कार, {name}.",
        "Gujarati": "ફરીથી નમસ્તે, {name}.",
        "Rajasthani": "फेरूं राम राम सा, {name}।",
    },

    "greet_regular": {
        "English": "Good to see you again, {name}. Always a pleasure.",
        "Hinglish": "{name}! Aapko dekhkar hamesha accha lagta hai.",
        "Hindi": "आपको फिर देखकर अच्छा लगा, {name}। हमेशा खुशी होती है।",
        "Marathi": "तुम्हाला पुन्हा पाहून आनंद झाला, {name}.",
        "Gujarati": "તમને ફરી જોઈને આનંદ થયો, {name}.",
        "Rajasthani": "थांने फेरूं देखर घणो चोखो लाग्यो, {name}।",
    },

    ################################################
    # Things going wrong
    ################################################

    "didnt_catch": {
        "English": "Sorry, I didn't catch that. Maybe next time.",
        "Hinglish": "Sorry, samajh nahi aaya. Next time try karte hain.",
        "Hindi": "माफ़ कीजिए, मैं समझ नहीं पाया। शायद अगली बार।",
        "Marathi": "माफ करा, मला समजलं नाही. कदाचित पुढच्या वेळी.",
        "Gujarati": "માફ કરશો, હું સમજ્યો નહીં. કદાચ આવતી વખતે.",
        "Rajasthani": "माफ करो सा, म्हूं समझ्यो कोनी। शायद अगली बार।",
    },

    "no_problem": {
        "English": "No problem.",
        "Hinglish": "Koi baat nahi.",
        "Hindi": "कोई बात नहीं।",
        "Marathi": "काही हरकत नाही.",
        "Gujarati": "કોઈ વાંધો નહીં.",
        "Rajasthani": "कोई बात कोनी।",
    },

    "couldnt_see": {
        "English": "Sorry, I couldn't see you well enough.",
        "Hinglish": "Sorry, main aapko theek se dekh nahi paaya.",
        "Hindi": "माफ़ कीजिए, मैं आपको ठीक से नहीं देख पाया।",
        "Marathi": "माफ करा, मला तुम्ही नीट दिसला नाहीत.",
        "Gujarati": "માફ કરશો, હું તમને બરાબર જોઈ શક્યો નહીં.",
        "Rajasthani": "माफ करो सा, म्हूं थांने ठीक सूं देख नीं सक्यो।",
    },
}


####################################################
# Which languages need an Indic TTS voice
####################################################

ROMAN_SCRIPT = {"English", "Hinglish"}


def needs_indic_voice(language):
    """
    True if this language is written in Devanagari or
    Gujarati script and will need a proper Indic TTS
    voice. A plain English engine turns these into noise.
    """

    return language not in ROMAN_SCRIPT


####################################################
# Lookup
####################################################

def phrase(key, language=DEFAULT_LANGUAGE, **fields):
    """
    Fetch a line, falling back to English if that
    language has no translation for the key.

    Missing translations degrade to English, not silence
    -- a robot that says nothing looks broken, one that
    switches language looks unfinished.
    """

    entry = PHRASES.get(key)

    if entry is None:
        return ""

    text = entry.get(language) or entry.get(DEFAULT_LANGUAGE, "")

    try:
        return text.format(**fields)
    except (KeyError, IndexError):
        return text


def available_languages():

    return sorted(
        {
            language
            for entry in PHRASES.values()
            for language in entry
        }
    )


####################################################

if __name__ == "__main__":

    print("Languages:", ", ".join(available_languages()))
    print()

    for language in available_languages():

        voice = (
            "needs Indic TTS" if needs_indic_voice(language)
            else "works with English TTS"
        )

        print(f"--- {language}  ({voice}) ---")
        print(" ", phrase("greet_first", language, name="Pranjal"))
        print(" ", phrase("greet_back_soon", language, name="Pranjal"))
        print(" ", phrase("ask_name", language))
        print()
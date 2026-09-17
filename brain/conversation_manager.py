"""
=========================================================
brain/conversation_manager.py

The central place conversations happen.

Author: Pranjal

FLOW
----
    wake word / face
            |
            v
        LISTEN        <- speech_listener (Whisper)
            |
            v
        THINK         <- LLM backend, with memory
            |
            v
        SPEAK         <- speech (TTS), in their language
            |
            v
    emotion + intent  <- face reacts, missions get queued

THREE DESIGN DECISIONS WORTH KNOWING
------------------------------------

1. THE LLM MUST NOT PROMISE WHAT VED CANNOT DO.

   An unconstrained model will cheerfully say "I'll bring
   your towels right away" when no delivery capability
   exists. The guest waits, nothing arrives, and the
   product looks broken in the worst possible way -- it
   lied.

   So the system prompt declares Ved's ACTUAL capability
   list, and every reply is parsed for an intent. If the
   model requests something not in the list, the intent
   is rejected and Ved says it cannot do that. Capability
   is data, declared in one place, not a hope.

2. IT MUST WORK WITH NO INTERNET.

   Hotel wifi fails. A robot that goes mute when it does
   is worse than one that was never smart. ScriptedBackend
   handles the common intents offline -- greetings, room
   directions, "what can you do" -- and the LLM is an
   ENHANCEMENT layered on top, not a dependency.

3. GUEST DATA SHOULD NOT LEAVE THE BUILDING CASUALLY.

   Sending "Mr Sharma in room 204 asked about his
   medication" to a cloud API is a privacy decision, not
   a technical one. redact() strips names and room
   numbers before anything goes out, and the reply is
   re-personalised locally. Under DPDP this distinction
   matters.

LATENCY
-------
Wake to first sound should be under ~1.5s or the pause
reads as a malfunction. Budget on a Pi 5:

    Whisper base    ~0.8s
    LLM round trip  ~1.2s   <- the problem
    Piper TTS       ~0.4s

That is why Ved says a filler ("Hmm...") the moment it
starts thinking. It buys a second and reads as natural
rather than as a hang.
=========================================================
"""

import json
import re
import threading
import time
from dataclasses import dataclass, field
from enum import Enum

from core.events import Event, event_bus
from core.state import RobotState, state_manager


####################################################
# What Ved can actually do
#
# The LLM is told exactly this list. Anything it asks
# for that is not here gets refused before it reaches
# the guest.
####################################################

@dataclass
class Capability:

    name: str
    description: str
    available: bool = True
    params: tuple = ()


CAPABILITIES = {
    "greet": Capability(
        "greet", "Say hello to someone"
    ),
    "answer": Capability(
        "answer", "Answer a general question conversationally"
    ),
    "remember_name": Capability(
        "remember_name", "Learn and remember a person's name",
        params=("name",)
    ),
    "guide_to_room": Capability(
        "guide_to_room", "Lead a guest to a room number",
        available=False,          # needs navigation
        params=("room",)
    ),
    "deliver_item": Capability(
        "deliver_item", "Take an item to a room",
        available=False,          # needs the chassis
        params=("item", "room")
    ),
    "call_staff": Capability(
        "call_staff", "Notify hotel staff that help is needed",
        available=False,          # needs a staff channel
        params=("reason",)
    ),
    "end_conversation": Capability(
        "end_conversation", "Politely finish the conversation"
    ),
}


def available_capabilities():

    return {
        name: cap for name, cap in CAPABILITIES.items()
        if cap.available
    }


####################################################
# Conversation state
####################################################

class Turn(Enum):

    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


# Conversation ends after this much silence.
CONVERSATION_TIMEOUT = 45.0

# Stop a conversation running forever.
MAX_TURNS = 25

# History sent to the LLM. Longer costs tokens and
# latency for diminishing benefit.
CONTEXT_TURNS = 8

# End the conversation after this many silent turns.
MAX_SILENT_TURNS = 3

# Said once when a reply doesn't come.
NUDGES = {
    "English": "Are you still there?",
    "Hinglish": "Aap wahan hain?",
    "Hindi": "क्या आप वहाँ हैं?",
    "Marathi": "तुम्ही तिथे आहात का?",
    "Gujarati": "તમે ત્યાં છો?",
    "Rajasthani": "थे बठै हो के?",
}


####################################################
# Privacy
####################################################

ROOM_PATTERN = re.compile(r"\b(room\s*)(\d{1,4}[A-Za-z]?)\b", re.I)


def redact(text, name=None):
    """
    Strip identifying detail before sending to a cloud LLM.

    Names become {{GUEST}}, room numbers become {{ROOM}}.
    Both are restored locally in the reply, so the guest
    still hears their own name -- it just never left the
    building.
    """

    if not text:
        return text, {}

    replacements = {}

    if name and name != "Unknown":
        pattern = re.compile(re.escape(name), re.I)

        if pattern.search(text):
            text = pattern.sub("{{GUEST}}", text)
            replacements["{{GUEST}}"] = name

    match = ROOM_PATTERN.search(text)

    if match:
        replacements["{{ROOM}}"] = match.group(2)
        text = ROOM_PATTERN.sub(r"\1{{ROOM}}", text)

    return text, replacements


def restore(text, replacements):

    for token, value in (replacements or {}).items():
        text = text.replace(token, value)

    return text


####################################################
# LLM backends
####################################################

class ScriptedBackend:
    """
    Offline fallback. No network, no model, no latency.

    Deliberately the DEFAULT. A hotel robot must keep
    working when the wifi does not, and most lobby
    exchanges are three turns of pleasantries anyway.
    """

    name = "scripted"

    # ORDER MATTERS. "Thank you, bye" contains both a
    # thanks and a farewell -- and people almost always
    # say them together. Farewell is checked FIRST, or
    # the conversation never ends and the guest walks
    # away from a robot still waiting for them.
    PATTERNS = [
        (
            r"\b(bye|goodbye|see you|alvida|chalta hoon|nikalta)\b",
            "Goodbye! Have a pleasant stay."
        ),
        (
            r"\b(hello|hi|hey|namaste|namaskar)\b",
            "Hello! How can I help you?"
        ),
        (
            r"\b(how are you|kaise ho|kaisi ho)\b",
            "I'm working well, thank you for asking."
        ),
        (
            r"\b(what can you do|what do you do|kya kar sakte)\b",
            "I can recognise guests, say hello, and answer "
            "simple questions. I'm still learning."
        ),
        (
            r"\b(your name|tumhara naam|aapka naam)\b",
            "I'm Ved."
        ),
        (
            r"\b(thank you|thanks|dhanyavaad|shukriya)\b",
            "You're very welcome."
        ),
        (
            r"\b(towel|water|food|room service|clean)\b",
            "I can't arrange that myself yet. Please ask "
            "at the front desk and they'll help right away."
        ),
    ]

    FAREWELL = re.compile(
        r"\b(bye|goodbye|see you|alvida|chalta hoon|nikalta)\b",
        re.I
    )

    def respond(self, message, context):

        lowered = (message or "").lower()

        # Farewell is decided separately from the reply,
        # so "thanks, bye" both thanks them AND ends.
        is_farewell = bool(self.FAREWELL.search(lowered))

        for pattern, reply in self.PATTERNS:

            if re.search(pattern, lowered):

                return {
                    "reply": reply,
                    "intent": (
                        "end_conversation" if is_farewell else "answer"
                    ),
                    "params": {},
                }

        return {
            "reply": (
                "I'm not sure I understood. Could you say "
                "that another way?"
            ),
            "intent": "end_conversation" if is_farewell else "answer",
            "params": {},
        }


class AnthropicBackend:
    """
    Claude via the Anthropic API.

    Needs ANTHROPIC_API_KEY in the environment and
    `pip install anthropic`.
    """

    name = "anthropic"

    def __init__(self, model="claude-sonnet-4-6", timeout=8.0):

        self.model = model
        self.timeout = timeout

        self._client = None

    ####################################################

    def _load(self):

        if self._client is not None:
            return self._client

        import anthropic

        self._client = anthropic.Anthropic()

        return self._client

    ####################################################

    @staticmethod
    def system_prompt(context):

        capabilities = "\n".join(
            f"  - {name}: {cap.description}"
            + (f" (needs: {', '.join(cap.params)})" if cap.params else "")
            for name, cap in available_capabilities().items()
        )

        language = context.get("language", "English")

        return f"""You are Ved, a service robot in an Indian hotel lobby.

SPEAK: reply in {language}. Keep it to ONE or TWO short
sentences -- this is spoken aloud, not read. No lists, no
markdown, no emoji.

YOU CAN ONLY DO THESE THINGS:
{capabilities}

CRITICAL: never promise anything outside that list. If
someone asks for something you cannot do, say so plainly
and suggest the front desk. Never say you will fetch,
deliver, book, or arrange anything.

Reply with ONLY a JSON object, no other text:
{{"reply": "what you say out loud", "intent": "one of the capability names", "params": {{}}}}"""

    ####################################################

    def respond(self, message, context):

        try:
            client = self._load()

            history = []

            for turn in context.get("history", [])[-CONTEXT_TURNS:]:
                history.append(
                    {
                        "role": turn["role"],
                        "content": turn["content"],
                    }
                )

            history.append({"role": "user", "content": message})

            response = client.messages.create(
                model=self.model,
                max_tokens=300,
                system=self.system_prompt(context),
                messages=history,
            )

            text = "".join(
                block.text for block in response.content
                if getattr(block, "type", "") == "text"
            ).strip()

            text = re.sub(r"^```(?:json)?|```$", "", text).strip()

            return json.loads(text)

        except Exception as exc:
            print(f"[CONV] Anthropic backend failed: {exc}")
            return None


class OllamaBackend:
    """
    Local model over Ollama. Fully offline, but a Pi 5
    will be slow -- realistically this runs on a laptop
    or a mini PC alongside the robot.
    """

    name = "ollama"

    def __init__(self, model="llama3.2:3b", host="http://localhost:11434"):

        self.model = model
        self.host = host

    def respond(self, message, context):

        try:
            import requests

            prompt = (
                AnthropicBackend.system_prompt(context)
                + f"\n\nGuest said: {message}\nJSON:"
            )

            response = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=15
            )

            text = response.json().get("response", "").strip()

            text = re.sub(r"^```(?:json)?|```$", "", text).strip()

            return json.loads(text)

        except Exception as exc:
            print(f"[CONV] Ollama backend failed: {exc}")
            return None


####################################################
# Fillers -- what Ved says while thinking
####################################################

FILLERS = {
    "English": ["Hmm.", "Let me think.", "One moment."],
    "Hinglish": ["Hmm, ek second.", "Sochne do.", "Ek minute."],
    "Hindi": ["एक पल।", "सोचने दीजिए।"],
    "Marathi": ["एक क्षण."],
    "Gujarati": ["એક ક્ષણ."],
    "Rajasthani": ["एक पल सा।"],
}


@dataclass
class ConversationResult:

    reply: str = ""
    intent: str = "answer"
    params: dict = field(default_factory=dict)
    rejected: bool = False
    backend: str = ""
    latency: float = 0.0


class ConversationManager:

    def __init__(
        self,
        backend=None,
        fallback=None,
        speak=None,
        listen=None,
        emotion=None,
        session=None,
        redact_pii=True,
    ):

        # LLM if configured, scripted otherwise. Scripted
        # is also the fallback when the LLM times out.
        self.backend = backend or ScriptedBackend()
        self.fallback = fallback or ScriptedBackend()

        self._speak = speak
        self._listen = listen
        self._emotion = emotion
        self._session = session

        self.redact_pii = redact_pii

        self.turn = Turn.IDLE

        self.partner = None
        self.language = "English"

        self.turns_taken = 0
        self.last_activity = time.time()

        # Consecutive silences. Waiting out a 45s timeout
        # while someone has clearly walked away is a hang
        # in everything but name.
        self.silent_turns = 0

        self._running = False
        self._lock = threading.Lock()

    ####################################################
    # Wiring -- late imports so this is testable alone
    ####################################################

    def speak(self, text, language=None):

        language = language or self.language

        if self._speak:
            return self._speak(text, language)

        try:
            from core.speech import speak as tts

            event_bus.publish(Event.SPEECH_START, {"text": text})

            tts(text, language)

            event_bus.publish(Event.SPEECH_END, {"text": text})

        except Exception:
            print(f"[VED] {text}")

    ####################################################

    def listen(self):

        if self._listen:
            return self._listen()

        try:
            from core.speech_listener import listen as stt

            return stt()

        except Exception:
            try:
                return input("You > ").strip() or None
            except (EOFError, KeyboardInterrupt):
                return None

    ####################################################

    def feel(self, emotion_name, intensity=1.0, reason=""):

        if self._emotion:
            return self._emotion(emotion_name, intensity, reason)

        try:
            from brain.emotion_engine import Emotion, emotion_engine

            emotion_engine.feel(
                Emotion[emotion_name.upper()], intensity, reason
            )

        except Exception:
            pass

    ####################################################
    # Capability enforcement
    ####################################################

    @staticmethod
    def validate(result):
        """
        Reject anything Ved cannot actually do.

        This is the guard that stops the robot promising a
        delivery it has no legs for.
        """

        intent = (result or {}).get("intent", "answer")

        capability = CAPABILITIES.get(intent)

        if capability is None:
            return False, (
                "Sorry, I'm not able to help with that. "
                "The front desk can assist you."
            )

        if not capability.available:
            return False, (
                "I can't do that yet, I'm sorry. Please ask "
                "at the front desk and they'll sort it out."
            )

        missing = [
            p for p in capability.params
            if p not in (result.get("params") or {})
        ]

        if missing:
            return False, (
                "I didn't quite catch the details. "
                "Could you say that again?"
            )

        return True, None

    ####################################################
    # One exchange
    ####################################################

    def respond_to(self, message):
        """
        Take what was heard, produce what to say.

        Returns a ConversationResult.
        """

        started = time.time()

        context = {
            "language": self.language,
            "partner": self.partner,
            "history": (
                self._session.get_history(CONTEXT_TURNS)
                if self._session else []
            ),
        }

        ################################################
        # Privacy: strip identifying detail
        ################################################

        outbound = message
        replacements = {}

        if self.redact_pii and self.backend.name != "scripted":
            outbound, replacements = redact(message, self.partner)

        ################################################
        # Ask the model, fall back if it fails
        ################################################

        raw = self.backend.respond(outbound, context)

        backend_used = self.backend.name

        if raw is None:
            raw = self.fallback.respond(message, context)
            backend_used = f"{self.fallback.name} (fallback)"

        ################################################
        # Enforce capability
        ################################################

        ok, refusal = self.validate(raw)

        if not ok:
            return ConversationResult(
                reply=refusal,
                intent="answer",
                rejected=True,
                backend=backend_used,
                latency=time.time() - started,
            )

        reply = restore(raw.get("reply", ""), replacements)

        return ConversationResult(
            reply=reply,
            intent=raw.get("intent", "answer"),
            params=raw.get("params") or {},
            backend=backend_used,
            latency=time.time() - started,
        )

    ####################################################
    # Full turn
    ####################################################

    def take_turn(self):
        """
        Listen, think, speak. Returns False to end the
        conversation.
        """

        ################################################
        # LISTEN
        ################################################

        self.turn = Turn.LISTENING

        state_manager.set(RobotState.LISTENING)

        self.feel("listening", 1.0, "waiting for speech")

        heard = self.listen()

        if not heard:

            self.silent_turns += 1

            # One silence is a pause. Three means they
            # left. Prompting once is polite; prompting
            # forever is a robot talking to an empty room.
            if self.silent_turns == 1:
                self.speak(
                    NUDGES.get(self.language, NUDGES["English"])
                )
                return True

            if self.silent_turns >= MAX_SILENT_TURNS:
                print("[CONV] No reply -- ending.")
                return False

            return not self.expired()

        self.silent_turns = 0

        print(f"[HEARD] {heard}")

        event_bus.publish(Event.SPEECH_HEARD, {"text": heard})

        self.last_activity = time.time()
        self.turns_taken += 1

        if self._session:
            self._session.add_message("user", heard)

        ################################################
        # THINK
        #
        # Say a filler FIRST. The LLM round trip is over
        # a second, and silence reads as a crash.
        ################################################

        self.turn = Turn.THINKING

        state_manager.set(RobotState.THINKING)

        self.feel("thinking", 0.8, "processing")

        if self.backend.name != "scripted":
            filler = FILLERS.get(self.language, FILLERS["English"])
            self.speak(filler[self.turns_taken % len(filler)])

        result = self.respond_to(heard)

        print(
            f"[CONV] {result.backend} "
            f"{result.latency:.2f}s -> {result.intent}"
            + ("  (REJECTED)" if result.rejected else "")
        )

        ################################################
        # SPEAK
        ################################################

        self.turn = Turn.SPEAKING

        state_manager.set(RobotState.SPEAKING)

        self.feel(
            "concerned" if result.rejected else "speaking",
            0.7 if result.rejected else 1.0,
            result.intent
        )

        self.speak(result.reply)

        if self._session:
            self._session.add_message("assistant", result.reply)

        ################################################
        # Intent -> the rest of the robot
        #
        # Published rather than executed here. The mission
        # manager owns doing things; conversation only
        # decides what was asked for.
        ################################################

        if result.intent not in ("answer", "end_conversation"):

            event_bus.publish(
                Event.TASK_STARTED,
                {
                    "intent": result.intent,
                    "params": result.params,
                    "partner": self.partner,
                }
            )

        if result.intent == "end_conversation":
            return False

        if self.turns_taken >= MAX_TURNS:
            print("[CONV] Turn limit reached.")
            return False

        return True

    ####################################################

    def expired(self):

        return (
            time.time() - self.last_activity
        ) > CONVERSATION_TIMEOUT

    ####################################################

    def start(self, partner=None, language="English", opener=None):
        """
        Begin a conversation and run it to completion.
        """

        with self._lock:

            if self._running:
                return False

            self._running = True

        self.partner = partner
        self.language = language
        self.turns_taken = 0
        self.silent_turns = 0
        self.last_activity = time.time()

        if self._session:
            self._session.set_partner(partner, language)

        print(f"\n[CONV] Started with {partner or 'someone'} [{language}]")

        try:
            if opener:
                self.speak(opener)

            while self.take_turn():

                if self.expired():
                    print("[CONV] Timed out.")
                    break

        except KeyboardInterrupt:
            print("\n[CONV] Interrupted.")

        finally:
            self.end()

        return True

    ####################################################

    def end(self):

        self.turn = Turn.IDLE

        self._running = False

        state_manager.set(RobotState.IDLE)

        self.feel("happy", 0.4, "conversation ended")

        print(f"[CONV] Ended after {self.turns_taken} turn(s).\n")


####################################################
# Backend selection
####################################################

def build_backend(prefer="auto"):
    """
    prefer: "auto" | "anthropic" | "ollama" | "scripted"

    auto tries the cloud, then local, then scripted. The
    scripted backend always works, which is the point.
    """

    import os

    if prefer in ("auto", "anthropic"):

        if os.environ.get("ANTHROPIC_API_KEY"):

            try:
                import anthropic  # noqa: F401
                return AnthropicBackend()
            except ImportError:
                pass

        if prefer == "anthropic":
            print("[CONV] Anthropic unavailable, using scripted.")

    if prefer in ("auto", "ollama"):

        try:
            import requests

            requests.get("http://localhost:11434", timeout=0.5)

            return OllamaBackend()

        except Exception:
            if prefer == "ollama":
                print("[CONV] Ollama unavailable, using scripted.")

    return ScriptedBackend()


####################################################
# Singleton
####################################################

conversation_manager = ConversationManager()


####################################################

if __name__ == "__main__":

    print("=" * 58)
    print("VED CONVERSATION MANAGER")
    print("=" * 58)

    ################################################
    # Capability enforcement
    ################################################

    print("\n--- What Ved will and won't promise ---\n")

    manager = ConversationManager(
        speak=lambda text, lang=None: print(f"  [VED] {text}"),
        listen=lambda: None,
    )

    for pretend_reply in [
        {"reply": "Hello there!", "intent": "greet", "params": {}},
        {
            "reply": "I'll bring towels to room 204 right away!",
            "intent": "deliver_item",
            "params": {"item": "towels", "room": "204"},
        },
        {
            "reply": "Follow me to your room.",
            "intent": "guide_to_room",
            "params": {"room": "204"},
        },
        {"reply": "Sure thing!", "intent": "book_taxi", "params": {}},
    ]:
        ok, refusal = manager.validate(pretend_reply)

        intent = pretend_reply["intent"]

        if ok:
            print(f"  {intent:<16} ALLOWED  -> {pretend_reply['reply']}")
        else:
            print(f"  {intent:<16} BLOCKED  -> {refusal}")

    print(
        "\n  The delivery promise is blocked because Ved has "
        "\n  no legs yet. Better than a guest waiting for towels."
    )

    ################################################
    # Privacy
    ################################################

    print("\n--- What leaves the building ---\n")

    original = "Pranjal here, can you check room 204 for me"

    redacted, replacements = redact(original, "Pranjal")

    print(f"  guest said : {original}")
    print(f"  sent to API: {redacted}")
    print(f"  restored   : {restore(redacted, replacements)}")

    ################################################
    # Offline conversation
    ################################################

    print("\n--- Full exchange, offline backend ---\n")

    script = iter([
        "Hello",
        "What can you do?",
        "Can you bring me some water?",
        "Thank you, bye",
    ])

    from core.session import Session

    demo = ConversationManager(
        backend=ScriptedBackend(),
        speak=lambda text, lang=None: print(f"  [VED]   {text}"),
        listen=lambda: next(script, None),
        emotion=lambda *a, **k: None,
        session=Session(),
    )

    demo.start(partner="Pranjal", language="English")

    print(f"Backend chosen by build_backend(): {build_backend().name}")
"""
=========================================================
brain/emotion_engine.py

Ved's emotional state.

Author: Pranjal

WHY THIS IS NOT JUST set_expression()
-------------------------------------
Right now every module calls set_expression("happy")
directly. Three problems with that:

1. NOBODY OWNS THE FACE. The greeter sets happy, the
   behaviour engine sets idle, the mission manager sets
   thinking -- and whichever ran last wins. There is no
   arbitration, so the face flickers.

2. EMOTIONS DON'T SNAP. A real reaction rises, holds,
   then fades. Setting "happy" and later setting "idle"
   is a light switch. Feeling happy at intensity 0.9 and
   letting it decay over eight seconds is an emotion.

3. NOTHING HAPPENS BETWEEN EVENTS. A robot whose face is
   frozen until something occurs looks switched off.

So: emotions are FELT with an intensity, they DECAY on
their own, the strongest one wins, and there is a
baseline mood underneath that drifts with how the day
has gone.

FLOW
----
    behaviour / events
            |
            v
      EmotionEngine        <- decides what is felt
            |
            v
      face_controller      <- UDP to the renderer
            |
            v
    eyes / eyebrows / mouth

THE RENDERER ONLY HAS NINE EXPRESSIONS
--------------------------------------
So richer emotions map onto them. "Concerned" and
"disappointed" both render as sad; "curious" renders as
surprised. Intensity is sent alongside, so the renderer
can use it later without changing this file.
=========================================================
"""

import random
import time
from dataclasses import dataclass
from enum import Enum

from core.events import Event, event_bus


####################################################
# Emotions
####################################################

class Emotion(Enum):

    NEUTRAL = "neutral"

    HAPPY = "happy"
    DELIGHTED = "delighted"

    CURIOUS = "curious"
    SURPRISED = "surprised"

    THINKING = "thinking"
    LISTENING = "listening"
    SPEAKING = "speaking"

    CONCERNED = "concerned"
    DISAPPOINTED = "disappointed"

    PLAYFUL = "playful"

    SLEEPY = "sleepy"

    ALARMED = "alarmed"


@dataclass
class EmotionSpec:
    """
    expression  which of the renderer's nine to show
    decay       intensity lost per second
    priority    breaks ties when two are felt at once
    valence     -1 negative .. +1 positive, feeds mood
    """

    expression: str
    decay: float
    priority: int
    valence: float


####################################################
# How each emotion behaves
#
# Decay rates are chosen so that:
#   - alarm and surprise fade fast (they're reflexes)
#   - happiness lingers (it's a mood, not a reflex)
#   - listening/speaking barely decay, because they're
#     driven by an activity that ends explicitly
####################################################

EMOTIONS = {
    Emotion.NEUTRAL: EmotionSpec("idle", 0.00, 0, 0.0),

    Emotion.HAPPY: EmotionSpec("happy", 0.12, 40, 0.6),
    Emotion.DELIGHTED: EmotionSpec("happy", 0.18, 50, 0.9),

    Emotion.CURIOUS: EmotionSpec("surprised", 0.30, 45, 0.2),

    # Surprise is a REFLEX, not a mood. It must cut
    # through whatever Ved was feeling -- an obstacle
    # appearing mid-greeting has to win, and win by a
    # clear margin rather than a coin toss.
    Emotion.SURPRISED: EmotionSpec("surprised", 0.55, 80, 0.1),

    Emotion.THINKING: EmotionSpec("thinking", 0.10, 55, 0.0),
    Emotion.LISTENING: EmotionSpec("listening", 0.04, 70, 0.1),
    Emotion.SPEAKING: EmotionSpec("speaking", 0.04, 75, 0.1),

    Emotion.CONCERNED: EmotionSpec("sad", 0.15, 65, -0.5),
    Emotion.DISAPPOINTED: EmotionSpec("sad", 0.20, 45, -0.6),

    Emotion.PLAYFUL: EmotionSpec("wink", 0.60, 35, 0.7),

    Emotion.SLEEPY: EmotionSpec("sleeping", 0.02, 20, 0.0),

    Emotion.ALARMED: EmotionSpec("surprised", 0.45, 95, -0.8),
}


# Below this, an emotion is considered finished.
INTENSITY_FLOOR = 0.08

# Mood drifts back toward neutral at this rate per second.
MOOD_DECAY = 0.004

# How much a single emotion nudges the long-term mood.
MOOD_INFLUENCE = 0.05

# Don't resend the same expression more often than this.
MIN_RESEND_INTERVAL = 0.15


@dataclass
class ActiveEmotion:

    emotion: Emotion
    intensity: float
    started: float
    reason: str = ""

    def spec(self):

        return EMOTIONS[self.emotion]

    def weight(self):
        """
        What this emotion is 'worth' right now.

        Priority scaled by how strongly it's still felt --
        so a fading alarm eventually loses to a fresh
        smile, without needing an explicit transition.
        """

        return self.spec().priority * self.intensity


class EmotionEngine:

    def __init__(self, send=None, idle_variation=True):

        # Injectable so this is testable without a face
        # process running.
        self._send = send

        self.active = {}

        # Long-term mood, -1..+1. Shifts slowly with
        # accumulated experience and biases how strongly
        # Ved reacts.
        self.mood = 0.0

        self.current_expression = "idle"
        self.current_emotion = Emotion.NEUTRAL

        self.idle_variation = idle_variation

        self._last_update = time.time()
        self._last_send = 0.0
        self._next_idle_flourish = time.time() + random.uniform(8, 18)

        self._history = []

    ####################################################
    # Output
    ####################################################

    def _dispatch(self, expression, intensity):

        now = time.time()

        unchanged = expression == self.current_expression

        if unchanged and (now - self._last_send) < MIN_RESEND_INTERVAL:
            return

        self.current_expression = expression
        self._last_send = now

        if self._send is not None:
            self._send(expression, intensity=round(intensity, 2))
            return

        # Late import so this module works with no face
        # package present (tests, headless runs).
        try:
            from face.face_controller import set_expression

            set_expression(expression, intensity=round(intensity, 2))

        except Exception:
            pass

    ####################################################
    # Feeling
    ####################################################

    def feel(self, emotion, intensity=1.0, reason=""):
        """
        Trigger an emotion.

        Feeling the same thing again REFRESHES it rather
        than stacking -- being greeted twice shouldn't
        make Ved twice as happy, it should keep it happy
        for longer.
        """

        if emotion not in EMOTIONS:
            return False

        # Mood biases reaction strength: a robot that has
        # had a good day reacts a little more warmly.
        spec = EMOTIONS[emotion]

        if spec.valence > 0:
            intensity *= 1.0 + max(0.0, self.mood) * 0.25
        elif spec.valence < 0:
            intensity *= 1.0 + max(0.0, -self.mood) * 0.25

        intensity = max(0.0, min(1.0, intensity))

        existing = self.active.get(emotion)

        if existing:
            existing.intensity = max(existing.intensity, intensity)
            existing.started = time.time()
            existing.reason = reason or existing.reason

        else:
            self.active[emotion] = ActiveEmotion(
                emotion=emotion,
                intensity=intensity,
                started=time.time(),
                reason=reason
            )

        # Nudge the long-term mood.
        self.mood += spec.valence * MOOD_INFLUENCE * intensity
        self.mood = max(-1.0, min(1.0, self.mood))

        self._history.append((time.time(), emotion.value, reason))

        if len(self._history) > 100:
            self._history.pop(0)

        # React immediately rather than waiting for the
        # next update tick.
        self.update()

        return True

    ####################################################

    def stop(self, emotion):
        """
        End an emotion now, rather than letting it decay.

        Used for activity-driven ones: when Ved finishes
        speaking, SPEAKING should end at once.
        """

        if emotion in self.active:
            del self.active[emotion]
            self.update()
            return True

        return False

    ####################################################

    def clear(self):

        self.active.clear()

        self.update()

    ####################################################
    # Tick
    ####################################################

    def update(self):
        """
        Decay emotions, pick the winner, drive the face.

        Call from the main loop. Cheap -- a handful of
        floats.
        """

        now = time.time()

        elapsed = now - self._last_update

        self._last_update = now

        if elapsed <= 0:
            elapsed = 0.0

        ################################################
        # Decay
        ################################################

        finished = []

        for emotion, active in self.active.items():

            active.intensity -= active.spec().decay * elapsed

            if active.intensity < INTENSITY_FLOOR:
                finished.append(emotion)

        for emotion in finished:
            del self.active[emotion]

        ################################################
        # Mood drifts back toward neutral
        ################################################

        if self.mood > 0:
            self.mood = max(0.0, self.mood - MOOD_DECAY * elapsed)
        elif self.mood < 0:
            self.mood = min(0.0, self.mood + MOOD_DECAY * elapsed)

        ################################################
        # Strongest feeling wins
        ################################################

        if not self.active:

            self.current_emotion = Emotion.NEUTRAL

            self._idle(now)

            return self.current_expression

        winner = max(self.active.values(), key=lambda a: a.weight())

        self.current_emotion = winner.emotion

        self._dispatch(winner.spec().expression, winner.intensity)

        return self.current_expression

    ####################################################
    # Idle behaviour
    ####################################################

    def _idle(self, now):
        """
        Keep the face alive when nothing is happening.

        A face that never changes between events reads as
        switched off. Occasionally Ved glances around or
        looks briefly curious -- small, infrequent, and
        never during a real emotion.
        """

        if not self.idle_variation:
            self._dispatch("idle", 0.0)
            return

        if now >= self._next_idle_flourish:

            self._next_idle_flourish = now + random.uniform(10, 25)

            # A brief flicker of curiosity, at low
            # intensity so any real event overrides it
            # instantly.
            self.feel(
                Emotion.CURIOUS,
                intensity=0.25,
                reason="idle glance"
            )

            return

        self._dispatch("idle", 0.0)

    ####################################################
    # Inspection
    ####################################################

    def state(self):

        return {
            "expression": self.current_expression,
            "emotion": self.current_emotion.value,
            "mood": round(self.mood, 3),
            "active": {
                e.value: round(a.intensity, 2)
                for e, a in self.active.items()
            },
        }

    def describe(self):
        """Human-readable, for logs and the dashboard."""

        if not self.active:
            tone = (
                "content" if self.mood > 0.15
                else "subdued" if self.mood < -0.15
                else "neutral"
            )
            return f"idle, mood {tone} ({self.mood:+.2f})"

        parts = [
            f"{e.value} {a.intensity:.2f}"
            for e, a in sorted(
                self.active.items(),
                key=lambda kv: -kv[1].weight()
            )
        ]

        return f"{' | '.join(parts)}  mood {self.mood:+.2f}"


####################################################
# Event wiring
#
# This is what makes the engine autonomous: the greeter
# and vision stack already publish these, so emotions
# happen without anyone calling feel() by hand.
####################################################

def connect_events(engine, bus=None):

    bus = bus or event_bus

    def on_recognised(data):
        name = (data or {}).get("name", "someone")
        engine.feel(Emotion.HAPPY, 0.85, f"recognised {name}")

    def on_unknown(data):
        engine.feel(Emotion.CURIOUS, 0.7, "unfamiliar face")

    def on_enrolled(data):
        name = (data or {}).get("name", "someone")
        engine.feel(Emotion.DELIGHTED, 1.0, f"met {name}")

    def on_lost(data):
        engine.feel(Emotion.CONCERNED, 0.5, "person left")

    def on_listening(data):
        engine.feel(Emotion.LISTENING, 1.0, "listening")

    def on_heard(data):
        engine.stop(Emotion.LISTENING)
        engine.feel(Emotion.THINKING, 0.8, "processing")

    def on_speaking(data):
        engine.stop(Emotion.THINKING)
        engine.feel(Emotion.SPEAKING, 1.0, "speaking")

    def on_spoken(data):
        engine.stop(Emotion.SPEAKING)

    def on_obstacle(data):
        engine.feel(Emotion.SURPRISED, 0.8, "obstacle")

    def on_emergency(data):
        engine.feel(Emotion.ALARMED, 1.0, "emergency")

    def on_battery_low(data):
        engine.feel(Emotion.CONCERNED, 0.4, "battery low")

    def on_task_failed(data):
        engine.feel(Emotion.DISAPPOINTED, 0.7, "task failed")

    def on_task_complete(data):
        engine.feel(Emotion.HAPPY, 0.6, "task complete")

    wiring = [
        (Event.FACE_RECOGNISED, on_recognised),
        (Event.FACE_UNKNOWN, on_unknown),
        (Event.FACE_ENROLLED, on_enrolled),
        (Event.PERSON_LOST, on_lost),
        (Event.WAKE_WORD, on_listening),
        (Event.SPEECH_HEARD, on_heard),
        (Event.SPEECH_START, on_speaking),
        (Event.SPEECH_END, on_spoken),
        (Event.OBSTACLE, on_obstacle),
        (Event.EMERGENCY, on_emergency),
        (Event.BATTERY_LOW, on_battery_low),
        (Event.TASK_FAILED, on_task_failed),
        (Event.TASK_COMPLETE, on_task_complete),
    ]

    for event, handler in wiring:
        bus.subscribe(event, handler)

    return engine


####################################################
# Singleton
####################################################

emotion_engine = EmotionEngine()


def feel(emotion, intensity=1.0, reason=""):

    return emotion_engine.feel(emotion, intensity, reason)


def update():

    return emotion_engine.update()


####################################################

if __name__ == "__main__":

    print("=" * 58)
    print("VED EMOTION ENGINE")
    print("=" * 58)

    sent = []

    engine = EmotionEngine(
        send=lambda expr, **kw: sent.append((expr, kw)),
        idle_variation=False
    )

    ################################################
    # Decay
    ################################################

    print("\n--- An emotion rises, holds, then fades ---\n")

    engine.feel(Emotion.HAPPY, 1.0, "greeted Pranjal")

    for step in range(9):
        engine.update()
        print(
            f"  t+{step}s   {engine.current_expression:<10} "
            f"{engine.describe()}"
        )
        time.sleep(1.0)

    ################################################
    # Arbitration
    ################################################

    print("\n--- Two feelings at once: strongest wins ---\n")

    engine.clear()

    engine.feel(Emotion.HAPPY, 0.9, "guest arrived")

    print(f"  happy only        -> {engine.current_expression}")

    engine.feel(Emotion.ALARMED, 0.9, "obstacle!")

    print(f"  + alarmed         -> {engine.current_expression}")

    time.sleep(1.6)
    engine.update()

    print(
        f"  alarm fades       -> {engine.current_expression}"
        f"   ({engine.describe()})"
    )

    ################################################
    # Mood
    ################################################

    print("\n--- Mood drifts with accumulated experience ---\n")

    engine.clear()

    print(f"  starting mood     {engine.mood:+.3f}")

    for _ in range(6):
        engine.feel(Emotion.HAPPY, 1.0, "good interaction")

    print(f"  after 6 greetings {engine.mood:+.3f}")

    for _ in range(4):
        engine.feel(Emotion.DISAPPOINTED, 1.0, "task failed")

    print(f"  after 4 failures  {engine.mood:+.3f}")

    ################################################
    # Event wiring
    ################################################

    print("\n--- Driven by the event bus ---\n")

    engine.clear()

    connect_events(engine)

    for event, data in [
        (Event.FACE_UNKNOWN, {}),
        (Event.FACE_ENROLLED, {"name": "Rahul"}),
        (Event.SPEECH_START, {}),
        (Event.SPEECH_END, {}),
        (Event.OBSTACLE, {"distance_cm": 20}),
    ]:
        event_bus.publish(event, data)

        print(
            f"  {event:<20} -> {engine.current_expression:<10} "
            f"({engine.current_emotion.value})"
        )

    print(f"\n  Total expression changes sent: {len(sent)}")
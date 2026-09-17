"""
=========================================================
greeter.py

Ved's social loop.

  - sees a known face      -> greets them by name
  - sees an unknown face   -> asks who they are, enrolls
  - remembers who it met   -> doesn't repeat itself

Run from the PROJECT ROOT:
    python3 -m vision.greeter

Author: Pranjal

DESIGN NOTES
------------
1. CONFIRMATION BEFORE ACTING. A face must be seen for
   several consecutive checks before Ved reacts. Single
   frames lie -- motion blur, a face on a TV, someone
   walking past the doorway. Reacting to one frame makes
   a robot that shouts at passers-by.

2. COOLDOWNS EVERYWHERE. Greeting cooldown per person,
   prompt cooldown for unknowns. Without them Ved says
   hello three times a second, which is the single
   fastest way to make a demo feel broken.

3. NO PROMPTING MID-CONVERSATION. Enrollment blocks the
   loop deliberately -- Ved should finish asking your
   name before it starts looking around again.

4. DEGRADES GRACEFULLY. Speech, TTS and the face display
   all route through interfaces.py, which falls back to
   terminal I/O. This runs today, with or without them.
=========================================================
"""

import re
import time

import cv2

from vision.camera import get_camera, release_camera
from vision.config import (
    ENROLL_SAMPLES,
    FACE_LOCK_THRESHOLD,
)
from vision.face_database import (
    add_templates,
    auto_learn,
    average_embeddings,
    get_language,
    normalise,
    set_profile,
)
from vision.face_engine import get_engine
from vision.greetings import (
    DEFAULT_LANGUAGE,
    parse_language,
    phrase,
)
from vision.interfaces import speak, listen, set_expression
from vision.social_memory import get_memory


####################################################
# Tuning
####################################################

# How often to run recognition (seconds).
CHECK_INTERVAL = 0.30

# Consecutive checks before Ved believes what it sees.
CONFIRM_KNOWN = 2
CONFIRM_UNKNOWN = 4

# A face narrower than this is too far away to talk to.
MIN_ENGAGE_WIDTH = 100

# Enrollment capture pacing.
SAMPLE_INTERVAL = 0.6
SAMPLE_TIMEOUT = 25.0

# Words people say instead of just their name.
NAME_NOISE = re.compile(
    r"\b(my name is|i am|i'm|this is|it's|call me|hello|hi|hey)\b",
    re.IGNORECASE
)

# Speech-to-text keeps every "um". Strip leading and
# trailing filler so "um hi this is Anjali speaking"
# resolves to "Anjali", not "Um Anjali".
FILLER_WORDS = {
    "um", "uh", "er", "ah", "oh", "well", "so", "okay",
    "ok", "yeah", "yes", "please", "sir", "madam",
    "speaking", "here", "there", "actually", "just",
}

DECLINE_WORDS = {
    "no", "nothing", "cancel", "stop", "later",
    "nevermind", "never mind", "skip",
}


####################################################
# Name handling
####################################################

def clean_name(raw):
    """
    Turn "um, hi my name is Pranjal" into "Pranjal".

    Returns None if nothing usable is left.
    """

    if not raw:
        return None

    text = NAME_NOISE.sub("", raw).strip()

    text = re.sub(r"[^A-Za-z\u0900-\u097F\s'-]", "", text)

    text = " ".join(text.split())

    if not text:
        return None

    if text.lower() in DECLINE_WORDS:
        return None

    # Drop filler words from both ends.
    words = [w for w in text.split() if w]

    while words and words[0].lower() in FILLER_WORDS:
        words.pop(0)

    while words and words[-1].lower() in FILLER_WORDS:
        words.pop()

    if not words:
        return None

    if " ".join(words).lower() in DECLINE_WORDS:
        return None

    # Keep it to two words -- speech recognition loves to
    # append a trailing sentence.
    parts = words[:2]

    name = " ".join(p.capitalize() for p in parts)

    if len(name) < 2 or len(name) > 40:
        return None

    return name


####################################################
# Greeting text
####################################################

def greeting_for(name, memory, language=None):
    """
    Pick a greeting based on history, in the person's own
    preferred language.
    """

    language = language or get_language(name) or DEFAULT_LANGUAGE

    visits = memory.visits(name)

    if visits == 0:
        key = "greet_first"

    elif (memory.seconds_since_seen(name) or 0) < 3600:
        key = "greet_back_soon"

    elif visits >= 5:
        key = "greet_regular"

    else:
        key = "greet_again"

    return phrase(key, language, name=name)


####################################################
# Greeter
####################################################

class Greeter:

    def __init__(self, show_preview=True):

        self.engine = get_engine()
        self.memory = get_memory()

        self.show_preview = show_preview

        self.cam = None

        self.last_check = 0.0
        self.streak_name = None
        self.streak_count = 0

        # Conditions we've already tried to learn this
        # session, so we don't re-check every tick.
        self._learn_attempted = set()

        self.status = "Waiting"

    ####################################################

    def _confirm(self, name):
        """
        Track consecutive sightings of the same identity.
        Returns the streak length.
        """

        if name == self.streak_name:
            self.streak_count += 1
        else:
            self.streak_name = name
            self.streak_count = 1

        return self.streak_count

    ####################################################

    def _reset_streak(self):

        self.streak_name = None
        self.streak_count = 0

    ####################################################

    def greet(self, name):

        language = get_language(name) or DEFAULT_LANGUAGE

        set_expression("happy")

        speak(greeting_for(name, self.memory, language))

        self.memory.record(name)

        self.status = f"Greeted {name} [{language}]"

        set_expression("idle")

    ####################################################

    def collect_samples(self, name, language=DEFAULT_LANGUAGE):
        """
        Capture ENROLL_SAMPLES embeddings from the live
        camera while the person stands there.

        Returns a list of embeddings.
        """

        embeddings = []

        deadline = time.time() + SAMPLE_TIMEOUT
        last_sample = 0.0

        prompts = [
            phrase("look_at_me", language),
            phrase("turn_left", language),
            phrase("turn_right", language),
        ]

        spoken = 0

        while (
            len(embeddings) < ENROLL_SAMPLES
            and time.time() < deadline
        ):

            frame = self.cam.get_frame()

            if frame is None:
                continue

            # Space the prompts across the capture.
            target_prompt = int(
                len(embeddings) / ENROLL_SAMPLES * len(prompts)
            )

            if target_prompt >= spoken and spoken < len(prompts):
                speak(prompts[spoken])
                spoken += 1

            if time.time() - last_sample < SAMPLE_INTERVAL:
                continue

            faces = self.engine.detect_faces(frame)

            if len(faces) != 1:
                continue

            face = faces[0]

            x1, _, x2, _ = map(int, face.bbox)

            if (x2 - x1) < MIN_ENGAGE_WIDTH:
                continue

            embeddings.append(normalise(face.embedding))

            last_sample = time.time()

            self.status = (
                f"Capturing {len(embeddings)}/{ENROLL_SAMPLES}"
            )

            print(f"  sample {len(embeddings)}/{ENROLL_SAMPLES}")

        return embeddings

    ####################################################

    def enroll_unknown(self, frame=None):
        """
        Ask who this is, which language they prefer, then
        learn their face.
        """

        self.memory.mark_unknown_prompt()

        ################################################
        # Name
        #
        # Asked in English -- we have no idea yet which
        # language they speak, and English is the safest
        # opener in an Indian hotel lobby.
        ################################################

        set_expression("surprised")

        speak(phrase("ask_name", DEFAULT_LANGUAGE))

        set_expression("listening")

        raw = listen(prompt="Name")

        name = clean_name(raw)

        if name is None:

            set_expression("idle")

            speak(
                phrase("didnt_catch", DEFAULT_LANGUAGE) if raw
                else phrase("no_problem", DEFAULT_LANGUAGE)
            )

            self.status = "Enrollment cancelled"
            return False

        ################################################
        # Language preference
        #
        # Everything after this point is spoken in their
        # own language -- which is the whole point.
        ################################################

        speak(phrase("ask_language", DEFAULT_LANGUAGE))

        set_expression("listening")

        language = parse_language(listen(prompt="Language"))

        if language is None:
            language = DEFAULT_LANGUAGE
            print("[ENROLL] No language understood, using English")
        else:
            print(f"[ENROLL] Language: {language}")

        ################################################
        # Capture
        ################################################

        set_expression("speaking")

        speak(phrase("hold_still", language, name=name))

        set_expression("idle")

        embeddings = self.collect_samples(name, language)

        if len(embeddings) < 2:

            speak(phrase("couldnt_see", language))

            self.status = "Enrollment failed"

            set_expression("sad")
            time.sleep(1.0)
            set_expression("idle")

            return False

        ################################################
        # Save
        #
        # Average WITHIN the session (same person, same
        # light, seconds apart) then add as ONE template
        # alongside any other conditions already stored.
        ################################################

        condition = self._condition_label(frame)

        add_templates(
            name,
            average_embeddings(embeddings),
            condition=condition
        )

        set_profile(name, preferred_language=language)

        self.engine.reload_database()

        set_expression("happy")

        speak(phrase("enrolled", language, name=name))

        self.memory.record(name)

        self.status = f"Enrolled {name} [{language}]"

        print(
            f"[ENROLL] {name} from {len(embeddings)} samples "
            f"[{condition}, {language}]"
        )

        set_expression("idle")

        return True

    ####################################################

    @staticmethod
    def _condition_label(frame):
        """
        Label the lighting so face_database can track
        which conditions a person is covered for.
        """

        if frame is None:
            return "default"

        from vision.camera import frame_brightness

        brightness = frame_brightness(frame)

        if brightness >= 120:
            return "bright"

        if brightness >= 70:
            return "indoor"

        if brightness >= 35:
            return "dim"

        return "dark"

    ####################################################

    def _maybe_learn(self, frame, name, score):
        """
        Silently add a template if this is a lighting
        condition we have no coverage for.

        Deliberately only runs on CONFIDENT matches. A
        database that learns from marginal matches
        gradually poisons itself -- each bad template
        makes the next bad match easier to accept.
        """

        if frame is None:
            return

        condition = self._condition_label(frame)

        # Rate-limit: at most one learning attempt per
        # person per run of the loop-check interval.
        key = (name, condition)

        if key in self._learn_attempted:
            return

        self._learn_attempted.add(key)

        face = self.engine.get_face(frame)

        if face is None:
            return

        learned = auto_learn(
            name,
            normalise(face.embedding),
            condition,
            score
        )

        if learned:
            self.engine.reload_database()
            self.status = f"{name} (learned {learned})"

    ####################################################

    def handle(self, frame):
        """
        One recognition tick.
        """

        results = self.engine.recognize_all(frame)

        if not results:
            self._reset_streak()
            self.status = "Waiting"
            return results

        closest = results[0]

        x1, _, x2, _ = closest["box"]

        # Too far away to be talking to Ved.
        if (x2 - x1) < MIN_ENGAGE_WIDTH:
            self._reset_streak()
            self.status = "Someone in view, too far"
            return results

        name = closest["name"]
        score = closest["score"]

        ################################################
        # Known person
        ################################################

        if name != "Unknown" and score >= FACE_LOCK_THRESHOLD:

            streak = self._confirm(name)

            if streak < CONFIRM_KNOWN:
                return results

            # Quietly improve coverage while we are
            # confident. Costs nothing, asks nothing.
            self._maybe_learn(frame, name, score)

            if self.memory.should_greet(name):
                self.greet(name)
                self._reset_streak()
            else:
                self.status = f"{name} (already greeted)"

            return results

        ################################################
        # Partially recognised -- the dead zone
        #
        # Score is above RECOGNISE but below LOCK. We
        # probably know this person, just not confidently
        # (poor light, bad angle, only one template).
        #
        # Do NOT enroll them. Enrolling here creates a
        # duplicate entry for someone already in the
        # database, and every duplicate makes future
        # matching worse.
        ################################################

        if name != "Unknown":

            self._reset_streak()

            self.status = (
                f"{name}? unsure ({score:.2f}) "
                f"-- need {FACE_LOCK_THRESHOLD:.2f}"
            )

            return results

        ################################################
        # Genuinely unknown
        ################################################

        streak = self._confirm("Unknown")

        if streak < CONFIRM_UNKNOWN:
            self.status = f"Unfamiliar face ({streak}/{CONFIRM_UNKNOWN})"
            return results

        if not self.memory.can_prompt_unknown():
            self.status = "Unknown (asked recently)"
            return results

        self.enroll_unknown(frame)

        self._reset_streak()

        return results

    ####################################################

    def draw(self, frame, results):

        for person in results:

            x1, y1, x2, y2 = person["box"]

            # Three states, three colours. Green meant
            # "recognised" before, which was misleading
            # at 0.49 -- confident enough to label, not
            # confident enough to greet.
            if person["name"] == "Unknown":
                colour = (0, 140, 255)          # orange
            elif person["score"] >= FACE_LOCK_THRESHOLD:
                colour = (0, 255, 0)            # green
            else:
                colour = (0, 255, 255)          # yellow

            cv2.rectangle(frame, (x1, y1), (x2, y2), colour, 2)

            cv2.putText(
                frame,
                f"{person['name']} ({person['score']:.2f})",
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                colour,
                2
            )

        cv2.putText(
            frame,
            self.status,
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 0),
            2
        )

        return frame

    ####################################################

    def run(self):

        self.cam = get_camera()

        if self.cam.wait_for_frame() is None:
            print("No frames from camera.")
            return

        print("=" * 52)
        print("VED GREETER")
        print("  Walk into view. ESC to quit.")
        print("=" * 52)

        set_expression("idle")

        results = []

        try:
            while True:

                frame = self.cam.get_frame()

                if frame is None:
                    continue

                now = time.time()

                if now - self.last_check >= CHECK_INTERVAL:
                    results = self.handle(frame)
                    self.last_check = time.time()

                if self.show_preview:

                    self.draw(frame, results)

                    cv2.imshow("Ved Greeter", frame)

                    if cv2.waitKey(1) & 0xFF == 27:
                        break

        except KeyboardInterrupt:
            print("\nInterrupted.")

        finally:
            cv2.destroyAllWindows()
            release_camera()
            set_expression("idle")
            print("Greeter stopped.")


####################################################

def main():

    Greeter().run()


if __name__ == "__main__":
    main()
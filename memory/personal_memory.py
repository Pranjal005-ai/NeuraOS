"""
=========================================================
memory/personal_memory.py

What Ved knows about each person.

Author: Pranjal

Replaces memory_parser.py + memory_search.py.

WHY THEY WERE MERGED
--------------------
The two files each held their own copy of the key list.
Adding "favourite film" meant editing both, with matching
strings, or it silently stopped working -- storable but
never recallable. Now ONE schema drives both directions.

WHY MEMORY IS PER PERSON
------------------------
Ved has face recognition. A single shared memory means
that when your mother-in-law says "my favourite food is
dhokla", it overwrites yours. In a home with four people
that is not a small bug -- it makes the feature actively
wrong. Every fact is stored against WHO said it.

THREE BUGS FIXED FROM THE OLD PARSER
------------------------------------
1. r"i am (.+)" matched almost anything. "I am hungry"
   stored name="hungry". "I am going to the kitchen"
   stored the whole phrase. That pattern now requires a
   name-shaped value and rejects common false positives.

2. command.lower() was applied before extraction, so
   names were stored lowercase and Ved replied "your name
   is pranjal". Matching is now case-insensitive while
   the ORIGINAL text is preserved.

3. (.+) is greedy. "My name is Pranjal and I live in
   Udaipur" stored the entire tail as the name. Values
   are now cut at conjunctions and punctuation.
=========================================================
"""

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MEMORY_FILE = DATA_DIR / "personal_memory.json"


# Words that end a value. Without these, a greedy (.+)
# swallows the rest of the sentence.
STOP_WORDS = r"(?:\s+(?:and|but|also|aur|lekin|because|kyunki)\b|[.,;!?]|$)"

# Things people say after "I am" that are obviously not
# names. Cheap, and catches the majority of misfires.
NOT_NAMES = {
    "hungry", "thirsty", "tired", "fine", "good", "ok",
    "okay", "sorry", "here", "back", "ready", "done",
    "busy", "late", "sure", "happy", "sad", "cold", "hot",
    "going", "coming", "leaving", "waiting", "looking",
    "not", "just", "still", "already", "always", "never",
}


@dataclass
class Fact:
    """
    key       schema key, e.g. "favourite_food"
    patterns  regexes that CAPTURE the value
    questions phrases that mean "tell me this"
    reply     how Ved says it back, {value} substituted
    validate  optional callable(value) -> bool
    """

    key: str
    patterns: tuple
    questions: tuple
    reply: str
    validate: object = None


def looks_like_name(value):
    """
    Reject the common "I am <adjective>" misfires.
    """

    cleaned = value.strip().strip(".!?,")

    if not cleaned or len(cleaned) > 40:
        return False

    words = cleaned.split()

    if len(words) > 3:
        return False

    if words[0].lower() in NOT_NAMES:
        return False

    # Must be letters (allow Devanagari and apostrophes).
    return bool(re.fullmatch(r"[A-Za-z\u0900-\u097F'\-\s.]+", cleaned))


####################################################
# The schema
#
# Add a fact here and it becomes both storable and
# recallable. One place, no duplication.
####################################################

SCHEMA = [

    Fact(
        key="name",
        patterns=(
            rf"my name is\s+(.+?){STOP_WORDS}",
            rf"mera naam\s+(.+?)\s*(?:hai|he){STOP_WORDS}",
            rf"call me\s+(.+?){STOP_WORDS}",
            rf"i\s*(?:'?m|am)\s+called\s+(.+?){STOP_WORDS}",
            # "i am X" / "i'm X" is LAST and validated,
            # because it is by far the most dangerous
            # pattern here. Note the alternation covers
            # BOTH "I am" and the contraction "I'm" --
            # "i'?\s*am" only matched the former, so
            # "I'm Rahul" silently stored nothing.
            rf"\bi\s*(?:'?m|am)\s+(.+?){STOP_WORDS}",
        ),
        questions=(
            "my name", "who am i", "mera naam", "naam kya",
        ),
        reply="Your name is {value}.",
        validate=looks_like_name,
    ),

    Fact(
        key="favourite_colour",
        patterns=(
            rf"my favou?rite colou?r is\s+(.+?){STOP_WORDS}",
            rf"i like the colou?r\s+(.+?){STOP_WORDS}",
            rf"mujhe\s+(.+?)\s+colou?r pasand{STOP_WORDS}",
        ),
        questions=(
            "favourite colour", "favorite color",
            "favourite color", "favorite colour",
            "colour pasand", "color pasand",
        ),
        reply="Your favourite colour is {value}.",
    ),

    Fact(
        key="favourite_food",
        patterns=(
            rf"my favou?rite (?:food|dish) is\s+(.+?){STOP_WORDS}",
            rf"i love eating\s+(.+?){STOP_WORDS}",
            rf"mujhe\s+(.+?)\s+(?:khana )?pasand hai{STOP_WORDS}",
        ),
        questions=(
            "favourite food", "favorite food",
            "favourite dish", "favorite dish",
            "khana pasand",
        ),
        reply="Your favourite food is {value}.",
    ),

    Fact(
        key="city",
        patterns=(
            rf"i live in\s+(.+?){STOP_WORDS}",
            rf"my city is\s+(.+?){STOP_WORDS}",
            rf"i'?m from\s+(.+?){STOP_WORDS}",
            # No STOP_WORDS here: "rehta hoon" has a
            # trailing word, so requiring a stop straight
            # after "rehta" never matched.
            rf"main\s+(.+?)\s+(?:mein|me)\s+reh(?:ta|ti)\b",
        ),
        questions=(
            "my city", "where do i live", "kahan rehta",
        ),
        reply="You live in {value}.",
    ),

    Fact(
        key="birthday",
        patterns=(
            rf"my birthday is\s+(?:on\s+)?(.+?){STOP_WORDS}",
            rf"i was born on\s+(.+?){STOP_WORDS}",
            rf"mera birthday\s+(.+?)\s*(?:hai|he){STOP_WORDS}",
        ),
        questions=(
            "my birthday", "when was i born", "mera birthday",
        ),
        reply="Your birthday is {value}.",
    ),

    Fact(
        key="job",
        patterns=(
            rf"i work (?:as|at)\s+(?:an?\s+)?(.+?){STOP_WORDS}",
            rf"my job is\s+(.+?){STOP_WORDS}",
            rf"i'?m an?\s+(engineer|doctor|teacher|student|nurse"
            rf"|manager|chef|driver|designer|developer){STOP_WORDS}",
        ),
        questions=(
            "my job", "what do i do", "where do i work",
        ),
        reply="You work as {value}.",
    ),

    Fact(
        key="room",
        patterns=(
            rf"my room (?:is|number is)\s+(.+?){STOP_WORDS}",
            rf"i'?m in room\s+(.+?){STOP_WORDS}",
            rf"mera room\s+(.+?)\s*(?:hai|he){STOP_WORDS}",
        ),
        questions=(
            "my room", "which room", "mera room",
        ),
        reply="You're in room {value}.",
    ),
]


SCHEMA_BY_KEY = {fact.key: fact for fact in SCHEMA}


####################################################
# Extraction
####################################################

def clean_value(value):

    value = value.strip().strip(".,;!?\"'")

    # Collapse whitespace.
    value = " ".join(value.split())

    return value


def parse(text):
    """
    Pull facts out of something a person said.

    Returns [(key, value)] -- possibly several, because
    "I'm Pranjal and I live in Udaipur" contains two.

    IMPORTANT: matching is case-insensitive but the
    ORIGINAL casing is preserved in the value.
    """

    if not text:
        return []

    found = []

    for fact in SCHEMA:

        for pattern in fact.patterns:

            match = re.search(pattern, text, re.IGNORECASE)

            if not match:
                continue

            value = clean_value(match.group(1))

            if not value:
                continue

            if fact.validate and not fact.validate(value):
                # Wrong shape -- try the next pattern
                # rather than storing rubbish.
                continue

            found.append((fact.key, value))

            break

    return found


def question_for(text):
    """
    Which fact is this asking about? None if it isn't.
    """

    if not text:
        return None

    lowered = text.lower()

    for fact in SCHEMA:
        for phrase in fact.questions:
            if phrase in lowered:
                return fact.key

    return None


####################################################
# Storage
####################################################

class PersonalMemory:

    def __init__(self, path=MEMORY_FILE):

        self.path = Path(path)

        # {person: {key: {"value", "at"}}}
        self.people = {}

        DATA_DIR.mkdir(parents=True, exist_ok=True)

        self.load()

    ####################################################

    def remember(self, person, key, value):
        """
        Store a fact against a specific person.
        """

        if not person:
            person = "Unknown"

        if key not in SCHEMA_BY_KEY:
            return False

        entry = self.people.setdefault(person, {})

        previous = entry.get(key, {}).get("value")

        entry[key] = {
            "value": value,
            "at": time.time(),
        }

        self.save()

        if previous and previous != value:
            print(
                f"[MEMORY] {person}: {key} "
                f"'{previous}' -> '{value}'"
            )
        else:
            print(f"[MEMORY] {person}: {key} = '{value}'")

        return True

    ####################################################

    def recall(self, person, key):
        """
        A stored value, or None.
        """

        return (
            self.people
            .get(person or "Unknown", {})
            .get(key, {})
            .get("value")
        )

    ####################################################

    def learn_from(self, person, text):
        """
        Extract and store everything in one utterance.

        Returns the keys learned.
        """

        learned = []

        for key, value in parse(text):

            if self.remember(person, key, value):
                learned.append(key)

        return learned

    ####################################################

    def answer(self, person, text):
        """
        Answer a question about a stored fact.

        Returns (reply, known):
            reply -- what to say, or None if not a
                     memory question at all
            known -- whether Ved actually knew

        The two-value return matters. The old version
        returned None both for "not a memory question"
        and for "asked, but I don't know" -- so Ved
        stayed silent when it should have admitted it
        didn't know.
        """

        key = question_for(text)

        if key is None:
            return None, False

        value = self.recall(person, key)

        if value is None:
            return (
                "I don't think you've told me that yet.",
                False
            )

        return SCHEMA_BY_KEY[key].reply.format(value=value), True

    ####################################################

    def profile(self, person):
        """Everything known about someone."""

        return {
            key: entry["value"]
            for key, entry in self.people.get(person, {}).items()
        }

    ####################################################

    def forget(self, person, key=None):
        """
        Delete one fact, or everything about a person.

        Needed for DPDP: a person must be able to have
        their data erased on request.
        """

        if person not in self.people:
            return False

        if key is None:
            del self.people[person]
        elif key in self.people[person]:
            del self.people[person][key]
        else:
            return False

        self.save()

        return True

    ####################################################

    def known_people(self):

        return sorted(self.people.keys())

    ####################################################

    def save(self):

        try:
            tmp = self.path.with_suffix(".tmp")

            with open(tmp, "w") as f:
                json.dump(
                    {"people": self.people},
                    f, indent=2, ensure_ascii=False
                )

            tmp.replace(self.path)

            return True

        except Exception as exc:
            print(f"[MEMORY] Could not save: {exc}")
            return False

    ####################################################

    def load(self):

        if not self.path.exists():
            return 0

        try:
            with open(self.path) as f:
                self.people = json.load(f).get("people", {})

        except Exception as exc:
            print(f"[MEMORY] Could not load: {exc}")
            self.people = {}

        return len(self.people)


####################################################
# Singleton
####################################################

personal_memory = PersonalMemory()


####################################################

if __name__ == "__main__":

    print("=" * 58)
    print("VED PERSONAL MEMORY")
    print("=" * 58)

    ################################################
    # The bug that mattered most
    ################################################

    print("\n--- 'I am ...' no longer eats everything ---\n")

    for text in [
        "I am Pranjal",
        "I am hungry",
        "I am going to the kitchen",
        "I am tired, can you help",
        "I'm Rahul Sharma",
        "I am not sure",
    ]:
        found = parse(text)

        result = (
            f"name = '{dict(found)['name']}'"
            if "name" in dict(found) else "nothing stored"
        )

        print(f"  {text:<32} -> {result}")

    ################################################
    # Greedy capture
    ################################################

    print("\n--- Values are cut at conjunctions ---\n")

    text = "My name is Pranjal and I live in Udaipur"

    print(f"  {text!r}\n")

    for key, value in parse(text):
        print(f"    {key:<10} = '{value}'")

    print("\n  Two separate facts, not one mangled string.")

    ################################################
    # Case preserved
    ################################################

    print("\n--- Original casing survives ---\n")

    print(f"  {parse('my name is Pranjal')}")
    print("  (the old parser stored 'pranjal')")

    ################################################
    # Per person
    ################################################

    print("\n--- Facts belong to a person ---\n")

    memory = PersonalMemory(DATA_DIR / "_demo_memory.json")

    memory.learn_from("Pranjal", "My favourite food is rajma chawal")
    memory.learn_from("Anjali", "My favourite food is dhokla")

    print()

    for person in memory.known_people():
        print(f"  {person:<10} {memory.profile(person)}")

    print("\n  One shared memory would have overwritten one.")

    ################################################
    # Answering
    ################################################

    print("\n--- Answering, including 'I don't know' ---\n")

    for person, question in [
        ("Pranjal", "what is my favourite food"),
        ("Anjali", "what is my favourite food"),
        ("Pranjal", "what is my birthday"),
        ("Pranjal", "what's the weather like"),
    ]:
        reply, known = memory.answer(person, question)

        print(
            f"  {person:<9} {question:<28} -> "
            + (reply if reply else "(not a memory question)")
        )

    print(
        "\n  Note the birthday case: Ved says it doesn't know,"
        "\n  rather than staying silent like the old version."
    )

    ################################################
    # Hinglish
    ################################################

    print("\n--- Hinglish input ---\n")

    for text in [
        "mera naam Vikram hai",
        "main Udaipur mein rehta hoon",
    ]:
        print(f"  {text:<32} -> {parse(text)}")

    (DATA_DIR / "_demo_memory.json").unlink(missing_ok=True)
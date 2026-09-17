"""
=========================================================
social_memory.py

Remembers who Ved has met and when.

Author: Pranjal

WHY THIS EXISTS
---------------
Recognition alone gives you "that is Pranjal" on every
single frame. What makes Ved feel like a robot rather
than a demo is knowing it ALREADY said hello two minutes
ago, and that this is Pranjal's fourth visit, not his
first.

Persisted to disk, so a reboot doesn't wipe the fact that
Ved has met someone. That matters for a hotel: a guest
who gets greeted as a stranger every morning is worse
than one who isn't greeted at all.
=========================================================
"""

import json
import threading
import time
from pathlib import Path

from vision.config import VISION_DIR


MEMORY_FILE = VISION_DIR / "social_memory.json"

# Don't greet the same person again within this window.
GREET_COOLDOWN = 180.0

# After enrolling or declining an unknown person, wait
# this long before asking anyone again. Unknown faces
# cannot be told apart, so this cooldown is global.
UNKNOWN_COOLDOWN = 60.0


class SocialMemory:

    def __init__(self, path=MEMORY_FILE):

        self.path = Path(path)
        self._lock = threading.Lock()

        self.people = {}
        self.last_unknown_prompt = 0.0

        self.load()

    ####################################################

    def load(self):

        if not self.path.exists():
            return

        try:
            with open(self.path) as f:
                data = json.load(f)

            self.people = data.get("people", {})

        except Exception as exc:
            print(f"[MEMORY] Could not load: {exc}")
            self.people = {}

    ####################################################

    def save(self):

        with self._lock:

            tmp = self.path.with_suffix(".tmp")

            try:
                with open(tmp, "w") as f:
                    json.dump(
                        {"people": self.people},
                        f,
                        indent=2
                    )

                # Atomic replace: a power cut mid-write
                # leaves the old file intact rather than
                # a truncated one.
                tmp.replace(self.path)

            except Exception as exc:
                print(f"[MEMORY] Could not save: {exc}")

    ####################################################

    def record(self, name):
        """
        Note that Ved has just seen and greeted someone.
        """

        now = time.time()

        entry = self.people.setdefault(
            name,
            {
                "first_seen": now,
                "last_seen": now,
                "visits": 0,
            }
        )

        entry["last_seen"] = now
        entry["visits"] = entry.get("visits", 0) + 1

        self.save()

        return entry

    ####################################################

    def should_greet(self, name):
        """
        True if enough time has passed to greet again.
        """

        entry = self.people.get(name)

        if entry is None:
            return True

        return (
            time.time() - entry.get("last_seen", 0)
            > GREET_COOLDOWN
        )

    ####################################################

    def is_first_meeting(self, name):

        return name not in self.people

    ####################################################

    def visits(self, name):

        return self.people.get(name, {}).get("visits", 0)

    ####################################################

    def seconds_since_seen(self, name):

        entry = self.people.get(name)

        if entry is None:
            return None

        return time.time() - entry.get("last_seen", 0)

    ####################################################

    def mark_unknown_prompt(self):
        """Called after asking (or failing to ask) a name."""

        self.last_unknown_prompt = time.time()

    ####################################################

    def can_prompt_unknown(self):

        return (
            time.time() - self.last_unknown_prompt
            > UNKNOWN_COOLDOWN
        )

    ####################################################

    def forget(self, name):

        if name in self.people:
            del self.people[name]
            self.save()
            return True

        return False


####################################################
# Lazy singleton
####################################################

_memory = None


def get_memory():

    global _memory

    if _memory is None:
        _memory = SocialMemory()

    return _memory


####################################################

if __name__ == "__main__":

    memory = get_memory()

    if not memory.people:
        print(f"No one met yet. File: {MEMORY_FILE}")
    else:
        print(f"{len(memory.people)} person(s) known\n")

        for name, entry in sorted(memory.people.items()):

            ago = memory.seconds_since_seen(name)

            print(
                f"  {name:<18} "
                f"visits={entry.get('visits', 0):<4} "
                f"last seen {ago / 60:.1f} min ago"
            )
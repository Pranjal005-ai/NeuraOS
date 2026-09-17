"""
=========================================================
core/session.py

Conversation session for Project Ved.

Author: Pranjal

WHAT CHANGED AND WHY
--------------------
Session no longer keeps its own copy of the robot state.

It used to hold `self.state` while state_manager held
another. Both claimed to be authoritative, robot_manager
used one and session.wake() set the other, and the two
would silently drift apart. The stale one always wins an
argument at the worst possible moment.

Now Session DELEGATES every state call to state_manager.
The properties still work, so existing code that reads
session.state keeps running -- but there is exactly one
source of truth underneath.

Session's real job is the conversation: history, turn
tracking, and knowing who Ved is currently talking to.
=========================================================
"""

import time

from core.state import RobotState, state_manager


# Conversations that go quiet for this long are over.
CONVERSATION_TIMEOUT = 120.0

# Cap history so a robot left running for a week doesn't
# slowly eat all its RAM.
MAX_HISTORY = 200


class Session:

    def __init__(self, manager=None):

        self.manager = manager or state_manager

        self.chat_history = []

        # Who Ved is talking to right now, if anyone.
        self.partner = None
        self.partner_language = "English"

        self.last_activity = time.time()

    ####################################################
    # State -- delegated, not duplicated
    ####################################################

    @property
    def state(self):

        return self.manager.get()

    @state.setter
    def state(self, value):

        self.manager.set(value)

    def set_state(self, state):

        return self.manager.set(state)

    def get_state(self):

        return self.manager.get()

    ####################################################
    # Wake / sleep
    ####################################################

    def wake(self, partner=None, language="English"):

        self.last_activity = time.time()

        if partner:
            self.partner = partner
            self.partner_language = language

        return self.manager.set(
            RobotState.LISTENING,
            reason=f"woken by {partner}" if partner else "woken"
        )

    def sleep(self):

        self.partner = None

        return self.manager.set(RobotState.SLEEPING)

    def is_active(self):

        return self.manager.get() != RobotState.SLEEPING

    ####################################################
    # Conversation partner
    ####################################################

    def set_partner(self, name, language="English"):
        """
        Who Ved is speaking with. Lets replies stay in
        their language without re-looking-up every turn.
        """

        if name != self.partner:
            self.clear_history()

        self.partner = name
        self.partner_language = language
        self.last_activity = time.time()

    def conversation_expired(self):
        """
        True if the conversation has gone quiet long
        enough to be considered finished.
        """

        return (
            time.time() - self.last_activity
        ) > CONVERSATION_TIMEOUT

    ####################################################
    # History
    ####################################################

    def add_message(self, role, content):

        self.chat_history.append(
            {
                "role": role,
                "content": content,
                "at": time.time(),
            }
        )

        # Trim from the front, keeping recent context.
        if len(self.chat_history) > MAX_HISTORY:
            self.chat_history = self.chat_history[-MAX_HISTORY:]

        self.last_activity = time.time()

    def get_history(self, limit=None):
        """
        A copy, so callers can't mutate the session's
        internal state by accident.
        """

        history = list(self.chat_history)

        return history[-limit:] if limit else history

    def last_message(self):

        return self.chat_history[-1] if self.chat_history else None

    def clear_history(self):

        self.chat_history.clear()

    def turn_count(self):

        return sum(
            1 for m in self.chat_history if m["role"] == "user"
        )

    ####################################################
    # Reset
    ####################################################

    def reset(self):

        self.clear_history()

        self.partner = None
        self.partner_language = "English"
        self.last_activity = time.time()

        self.manager.set(RobotState.IDLE, reason="session reset")


####################################################
# Singleton
####################################################

session = Session()


####################################################

if __name__ == "__main__":

    print("=" * 52)
    print("VED SESSION")
    print("=" * 52)

    s = Session()

    s.wake("Pranjal", "Hinglish")

    s.add_message("assistant", "Arre Pranjal, wapas aa gaye!")
    s.add_message("user", "Room 204 mein towel bhej do")

    print(f"\nPartner   : {s.partner} ({s.partner_language})")
    print(f"State     : {s.state.value}")
    print(f"Turns     : {s.turn_count()}")

    ################################################
    # The point: one source of truth
    ################################################

    print("\n--- Session and state_manager stay in sync ---")

    s.set_state(RobotState.THINKING)

    print(f"session.state       : {s.state.value}")
    print(f"state_manager.get() : {state_manager.get().value}")
    print("(same object underneath -- they cannot drift)")
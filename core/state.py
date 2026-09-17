"""
=========================================================
core/state.py

Robot State Manager for Project Ved / NeuraOS

Author: Pranjal

WHAT CHANGED AND WHY
--------------------
1. THREE ORTHOGONAL AXES, not one enum.

   The old RobotState mixed activity (MOVING), deployment
   mode (HOTEL_MODE) and task (FACE_RECOGNITION) into a
   single value. But Ved can be in hotel mode, following
   a person, while running face recognition -- all at
   once. One enum cannot express that, so setting one
   silently erased another.

       state -> what am I doing right now
       mode  -> which deployment am I configured for
       task  -> what am I working on

2. EMERGENCY STOP IS PROTECTED.

   Previously any code anywhere could call
   set(RobotState.MOVING) and silently clear an emergency
   stop. Now, once latched, ONLY clear_emergency() can
   release it. Everything else is refused and logged.
   For the one state that means "stop, something is
   wrong", that guarantee is the whole point.

3. IT SURVIVES POWER LOSS.

   State is written to disk on every change. On boot,
   recover() tells you what Ved was doing when it died
   and what it should do about it. A robot that wakes
   mid-delivery with no memory is worse than one that
   refuses to move.

4. TRANSITIONS ARE OBSERVABLE.

   Subscribers get notified on change, so the face
   renderer, dashboard and behaviour engine can react
   without polling.
=========================================================
"""

import json
import threading
import time
from enum import Enum
from pathlib import Path


STATE_DIR = Path(__file__).resolve().parent.parent / "data"
STATE_FILE = STATE_DIR / "robot_state.json"

# A crash is only "recent" for this long. Older than
# this and Ved was probably just switched off normally.
RECOVERY_WINDOW = 600.0

# How often the heartbeat is written while running.
HEARTBEAT_INTERVAL = 5.0


####################################################
# What Ved is DOING
####################################################

class RobotState(Enum):

    BOOTING = "BOOTING"
    IDLE = "IDLE"
    SLEEPING = "SLEEPING"

    LISTENING = "LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"

    MOVING = "MOVING"
    FOLLOWING = "FOLLOWING"
    NAVIGATING = "NAVIGATING"
    SEARCHING = "SEARCHING"

    CHARGING = "CHARGING"
    DOCKING = "DOCKING"

    ERROR = "ERROR"
    EMERGENCY_STOP = "EMERGENCY_STOP"


####################################################
# Which deployment Ved is configured for
####################################################

class RobotMode(Enum):

    GENERAL = "GENERAL"
    HOTEL = "HOTEL"
    HOSPITAL = "HOSPITAL"
    DEMO = "DEMO"
    MAINTENANCE = "MAINTENANCE"


####################################################
# What Ved is working on
####################################################

class RobotTask(Enum):

    NONE = "NONE"

    GREETING = "GREETING"
    ENROLLING = "ENROLLING"

    FACE_RECOGNITION = "FACE_RECOGNITION"
    OBJECT_DETECTION = "OBJECT_DETECTION"
    QR_SCANNING = "QR_SCANNING"
    READING_TEXT = "READING_TEXT"

    DELIVERY = "DELIVERY"
    ESCORTING = "ESCORTING"
    PATROLLING = "PATROLLING"


####################################################
# States that mean "do not drive"
####################################################

BLOCKED_FROM_MOVING = {
    RobotState.EMERGENCY_STOP,
    RobotState.ERROR,
    RobotState.CHARGING,
    RobotState.SLEEPING,
}

MOVEMENT_STATES = {
    RobotState.MOVING,
    RobotState.FOLLOWING,
    RobotState.NAVIGATING,
    RobotState.SEARCHING,
    RobotState.DOCKING,
}


class StateManager:

    def __init__(self, path=STATE_FILE, autosave=True):

        self.path = Path(path)
        self.autosave = autosave

        self._lock = threading.RLock()

        self.state = RobotState.BOOTING
        self.mode = RobotMode.GENERAL
        self.task = RobotTask.NONE

        # Free-form detail about the current task, e.g.
        # {"room": "204", "item": "towels"}. Persisted, so
        # a delivery survives a reboot.
        self.context = {}

        self._emergency = False
        self._emergency_reason = None

        self._listeners = []

        self._last_change = time.time()
        self._started_at = time.time()

        self._previous_run = None

        STATE_DIR.mkdir(parents=True, exist_ok=True)

    ####################################################
    # Observers
    ####################################################

    def subscribe(self, callback):
        """
        callback(old_state, new_state, manager)

        Lets the face renderer and dashboard react to
        transitions instead of polling.
        """

        with self._lock:
            self._listeners.append(callback)

        return callback

    def unsubscribe(self, callback):

        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def _notify(self, old, new):

        # Copy so a callback that unsubscribes mid-loop
        # doesn't corrupt the iteration.
        with self._lock:
            listeners = list(self._listeners)

        for callback in listeners:
            try:
                callback(old, new, self)
            except Exception as exc:
                # One broken listener must not stop the
                # others, and must never take down the
                # state machine.
                print(f"[STATE] Listener failed: {exc}")

    ####################################################
    # Reading
    ####################################################

    def get(self):

        with self._lock:
            return self.state

    def get_mode(self):

        with self._lock:
            return self.mode

    def get_task(self):

        with self._lock:
            return self.task

    def snapshot(self):
        """Everything, as a plain dict."""

        with self._lock:
            return {
                "state": self.state.value,
                "mode": self.mode.value,
                "task": self.task.value,
                "context": dict(self.context),
                "emergency": self._emergency,
                "emergency_reason": self._emergency_reason,
                "since": self._last_change,
                "uptime": round(time.time() - self._started_at, 1),
            }

    def is_emergency(self):

        with self._lock:
            return self._emergency

    def can_move(self):
        """
        Ask before driving. Cheaper than discovering
        mid-corridor that we shouldn't have.
        """

        with self._lock:
            return (
                not self._emergency
                and self.state not in BLOCKED_FROM_MOVING
            )

    def is_moving(self):

        with self._lock:
            return self.state in MOVEMENT_STATES

    def seconds_in_state(self):

        with self._lock:
            return time.time() - self._last_change

    ####################################################
    # Writing
    ####################################################

    def set(self, state, reason=None):
        """
        Change the activity state.

        Refused while an emergency stop is latched --
        use clear_emergency() first, deliberately.
        """

        if not isinstance(state, RobotState):
            raise TypeError(f"Expected RobotState, got {type(state)}")

        with self._lock:

            if self._emergency and state != RobotState.EMERGENCY_STOP:
                print(
                    f"[STATE] REFUSED {state.value} -- emergency "
                    f"stop is latched ({self._emergency_reason}). "
                    f"Call clear_emergency() first."
                )
                return False

            if state == self.state:
                return True

            old = self.state

            self.state = state
            self._last_change = time.time()

            suffix = f"  ({reason})" if reason else ""

            print(f"[STATE] {old.value} -> {state.value}{suffix}")

        self._notify(old, state)

        if self.autosave:
            self.save()

        return True

    def set_mode(self, mode):

        if not isinstance(mode, RobotMode):
            raise TypeError(f"Expected RobotMode, got {type(mode)}")

        with self._lock:

            if mode == self.mode:
                return True

            print(f"[MODE] {self.mode.value} -> {mode.value}")

            self.mode = mode

        if self.autosave:
            self.save()

        return True

    def set_task(self, task, **context):
        """
        Set what Ved is working on, with detail.

            set_task(RobotTask.DELIVERY, room="204")
        """

        if not isinstance(task, RobotTask):
            raise TypeError(f"Expected RobotTask, got {type(task)}")

        with self._lock:

            self.task = task

            self.context = dict(context) if context else {}

            detail = (
                "  " + ", ".join(
                    f"{k}={v}" for k, v in self.context.items()
                )
                if self.context else ""
            )

            print(f"[TASK] {task.value}{detail}")

        if self.autosave:
            self.save()

        return True

    def clear_task(self):

        return self.set_task(RobotTask.NONE)

    ####################################################
    # Emergency
    ####################################################

    def emergency_stop(self, reason="unspecified"):
        """
        Latch an emergency stop. Nothing else can clear it.
        """

        with self._lock:

            already = self._emergency

            self._emergency = True
            self._emergency_reason = reason

            old = self.state

            self.state = RobotState.EMERGENCY_STOP
            self._last_change = time.time()

        if not already:
            print(f"\n[STATE] *** EMERGENCY STOP *** ({reason})\n")
            self._notify(old, RobotState.EMERGENCY_STOP)

        # Save even if it was already latched -- the
        # reason may have changed and we want it on disk.
        self.save()

        return True

    def clear_emergency(self, to=RobotState.IDLE):
        """
        Release the latch. Deliberately explicit.
        """

        with self._lock:

            if not self._emergency:
                return False

            print(
                f"[STATE] Emergency cleared "
                f"(was: {self._emergency_reason})"
            )

            self._emergency = False
            self._emergency_reason = None

            old = self.state
            self.state = to
            self._last_change = time.time()

        self._notify(old, to)

        if self.autosave:
            self.save()

        return True

    ####################################################
    # Persistence
    ####################################################

    def save(self):
        """
        Write state to disk. Atomic, so a power cut
        mid-write leaves the previous file intact rather
        than a truncated one.
        """

        try:
            data = self.snapshot()

            data["saved_at"] = time.time()
            data["clean_shutdown"] = False

            tmp = self.path.with_suffix(".tmp")

            with open(tmp, "w") as f:
                json.dump(data, f, indent=2)

            tmp.replace(self.path)

            return True

        except Exception as exc:
            print(f"[STATE] Could not save: {exc}")
            return False

    def mark_clean_shutdown(self):
        """
        Call on a normal exit. The difference between this
        and its absence is how recover() knows whether Ved
        crashed or was switched off properly.
        """

        try:
            data = self.snapshot()

            data["saved_at"] = time.time()
            data["clean_shutdown"] = True

            with open(self.path, "w") as f:
                json.dump(data, f, indent=2)

            print("[STATE] Clean shutdown recorded.")

            return True

        except Exception as exc:
            print(f"[STATE] Could not record shutdown: {exc}")
            return False

    def load(self):
        """
        Read the previous run's state, without applying it.
        """

        if not self.path.exists():
            return None

        try:
            with open(self.path) as f:
                data = json.load(f)

            self._previous_run = data

            return data

        except Exception as exc:
            print(f"[STATE] Could not load: {exc}")
            return None

    ####################################################
    # Recovery
    ####################################################

    def recover(self):
        """
        Decide what to do about the previous run.

        Returns a dict:
            {"action": ..., "reason": ..., "previous": ...}

        action is one of:
            "fresh"    -- nothing to recover
            "resume"   -- a task was interrupted
            "clear"    -- was mid-movement, do not resume
            "blocked"  -- died in emergency stop

        Deliberately RETURNS a decision rather than acting
        on it. A robot that silently resumes driving after
        a power cut is dangerous; the caller should decide,
        and usually ask a human.
        """

        previous = self.load()

        if previous is None:
            return {
                "action": "fresh",
                "reason": "No previous state file.",
                "previous": None,
            }

        age = time.time() - previous.get("saved_at", 0)

        ################################################
        # Clean shutdown
        ################################################

        if previous.get("clean_shutdown"):
            return {
                "action": "fresh",
                "reason": "Previous run shut down cleanly.",
                "previous": previous,
            }

        ################################################
        # Died in emergency stop -- stay stopped
        ################################################

        if previous.get("emergency"):
            return {
                "action": "blocked",
                "reason": (
                    "Previous run ended in EMERGENCY STOP "
                    f"({previous.get('emergency_reason')}). "
                    "Requires manual clearance."
                ),
                "previous": previous,
            }

        ################################################
        # Too long ago to be a crash
        ################################################

        if age > RECOVERY_WINDOW:
            return {
                "action": "fresh",
                "reason": (
                    f"Previous state is {age / 60:.0f} minutes "
                    "old -- treating as a normal restart."
                ),
                "previous": previous,
            }

        ################################################
        # Was it moving?
        ################################################

        state = previous.get("state")

        if state in {s.value for s in MOVEMENT_STATES}:
            return {
                "action": "clear",
                "reason": (
                    f"Crashed while {state}. Position is "
                    "unknown -- do not resume movement."
                ),
                "previous": previous,
            }

        ################################################
        # Had a task in progress
        ################################################

        task = previous.get("task", RobotTask.NONE.value)

        if task != RobotTask.NONE.value:
            return {
                "action": "resume",
                "reason": (
                    f"Task '{task}' was in progress "
                    f"{age:.0f}s ago."
                ),
                "previous": previous,
            }

        return {
            "action": "fresh",
            "reason": "Nothing in progress.",
            "previous": previous,
        }

    def apply_recovery(self, decision):
        """
        Act on a recovery decision. Caller's choice.
        """

        action = decision.get("action")
        previous = decision.get("previous") or {}

        if action == "blocked":

            self.emergency_stop(
                previous.get("emergency_reason", "recovered")
            )

            return False

        if action == "resume":

            try:
                self.set_task(
                    RobotTask(previous.get("task")),
                    **(previous.get("context") or {})
                )
            except (ValueError, TypeError):
                self.clear_task()

        try:
            self.set_mode(RobotMode(previous.get("mode", "GENERAL")))
        except (ValueError, TypeError):
            pass

        self.set(RobotState.IDLE, reason="recovered")

        return True


####################################################
# Singleton
####################################################

state_manager = StateManager()


####################################################

if __name__ == "__main__":

    print("=" * 52)
    print("VED STATE MANAGER")
    print("=" * 52)

    decision = state_manager.recover()

    print(f"\nRecovery: {decision['action'].upper()}")
    print(f"  {decision['reason']}\n")

    state_manager.apply_recovery(decision)

    ################################################
    # Demonstrate the axes are independent
    ################################################

    print("\n--- Three independent axes ---")

    state_manager.set_mode(RobotMode.HOTEL)
    state_manager.set_task(RobotTask.DELIVERY, room="204", item="towels")
    state_manager.set(RobotState.NAVIGATING)

    print(f"\n{state_manager.snapshot()}\n")

    ################################################
    # Demonstrate the emergency latch
    ################################################

    print("--- Emergency stop is protected ---")

    state_manager.emergency_stop("obstacle detected")

    print(f"can_move() -> {state_manager.can_move()}")

    state_manager.set(RobotState.MOVING)      # refused

    state_manager.clear_emergency()

    print(f"can_move() -> {state_manager.can_move()}")

    state_manager.mark_clean_shutdown()
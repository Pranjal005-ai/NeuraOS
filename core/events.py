"""
=========================================================
core/events.py

Event bus for Ved.

Author: Pranjal

WHAT CHANGED AND WHY
--------------------
1. THREAD SAFE. Ved now has a camera capture thread, a
   TTS thread and the main loop. Without a lock, a
   subscribe() during a publish() corrupts the iteration.

2. ERRORS ISOLATED. Previously one failing callback
   raised straight out of publish(), so every subscriber
   after it never ran -- and the publisher crashed too.
   A broken dashboard listener must not stop the motors
   from receiving an obstacle event.

3. UNSUBSCRIBE EXISTS. Without it, anything that
   subscribes lives forever.

4. WILDCARD LISTENERS. subscribe("*") sees everything --
   how the logger and dashboard get built without
   touching every publisher.
=========================================================
"""

import threading
import time
from collections import deque


####################################################
# Standard event names
#
# Strings are flexible but typo-prone: publishing
# "obstacle_detected" while listening for
# "obstacle.detected" fails silently. Use these.
####################################################

class Event:

    # Vision
    FACE_DETECTED = "face.detected"
    FACE_RECOGNISED = "face.recognised"
    FACE_UNKNOWN = "face.unknown"
    FACE_ENROLLED = "face.enrolled"
    PERSON_LOST = "person.lost"
    OBJECT_DETECTED = "object.detected"
    QR_SCANNED = "qr.scanned"

    # Interaction
    WAKE_WORD = "voice.wake"
    SPEECH_HEARD = "voice.heard"
    SPEECH_START = "voice.speaking"
    SPEECH_END = "voice.spoken"

    # Motion
    OBSTACLE = "motion.obstacle"
    ARRIVED = "motion.arrived"
    MOVEMENT_BLOCKED = "motion.blocked"

    # System
    STATE_CHANGED = "system.state"
    TASK_STARTED = "task.started"
    TASK_COMPLETE = "task.complete"
    TASK_FAILED = "task.failed"
    BATTERY_LOW = "system.battery_low"
    BATTERY_CRITICAL = "system.battery_critical"
    EMERGENCY = "system.emergency"
    ERROR = "system.error"


WILDCARD = "*"


class EventBus:

    def __init__(self, history=100):

        self._listeners = {}
        self._lock = threading.RLock()

        # Recent events, for debugging and the dashboard.
        # A robot in someone's lobby cannot be debugged
        # without knowing what just happened.
        self._history = deque(maxlen=history)

        self._counts = {}

    ####################################################

    def subscribe(self, event, callback):
        """
        Listen for an event. Use Event.* constants.

        subscribe(WILDCARD, cb) receives everything.
        Returns the callback, so it can be unsubscribed.
        """

        with self._lock:
            self._listeners.setdefault(event, []).append(callback)

        return callback

    ####################################################

    def unsubscribe(self, event, callback):

        with self._lock:

            handlers = self._listeners.get(event)

            if handlers and callback in handlers:
                handlers.remove(callback)
                return True

        return False

    ####################################################

    def publish(self, event, data=None):
        """
        Fire an event. Never raises -- a failing listener
        is logged and the rest still run.

        Returns the number of listeners that succeeded.
        """

        entry = {
            "event": event,
            "data": data,
            "at": time.time(),
        }

        with self._lock:

            self._history.append(entry)

            self._counts[event] = self._counts.get(event, 0) + 1

            # Copy before iterating: a listener that
            # subscribes or unsubscribes during dispatch
            # would otherwise mutate the list we're
            # walking.
            #
            # Tag each handler with how it wants to be
            # called. Specific listeners get the data;
            # wildcard listeners get the whole entry, so
            # they can see which event fired. Guessing at
            # call time and retrying on TypeError does not
            # work -- a listener that raises KeyError on
            # the wrong argument looks like a genuine bug,
            # not a calling-convention mismatch.
            handlers = [
                (cb, False)
                for cb in self._listeners.get(event, [])
            ]

            handlers += [
                (cb, True)
                for cb in self._listeners.get(WILDCARD, [])
            ]

        delivered = 0

        for callback, wants_entry in handlers:

            try:
                callback(entry if wants_entry else data)
                delivered += 1

            except Exception as exc:
                print(f"[EVENT] '{event}' listener failed: {exc}")

        return delivered

    ####################################################

    def listeners_for(self, event):

        with self._lock:
            return len(self._listeners.get(event, []))

    ####################################################

    def recent(self, count=20, event=None):
        """Recent events, newest last."""

        with self._lock:
            items = list(self._history)

        if event:
            items = [e for e in items if e["event"] == event]

        return items[-count:]

    ####################################################

    def stats(self):

        with self._lock:
            return dict(self._counts)

    ####################################################

    def clear(self):

        with self._lock:
            self._listeners.clear()
            self._history.clear()
            self._counts.clear()


####################################################
# Singleton
####################################################

event_bus = EventBus()


def publish(event, data=None):

    return event_bus.publish(event, data)


def subscribe(event, callback):

    return event_bus.subscribe(event, callback)


####################################################
# Bridge state changes onto the bus
####################################################

def connect_state_manager(manager=None):
    """
    Publish STATE_CHANGED whenever the state changes, so
    subscribers don't have to poll.
    """

    if manager is None:
        from core.state import state_manager as manager

    def on_change(old, new, mgr):
        event_bus.publish(
            Event.STATE_CHANGED,
            {
                "from": old.value,
                "to": new.value,
                "mode": mgr.get_mode().value,
                "task": mgr.get_task().value,
            }
        )

    manager.subscribe(on_change)

    return on_change


####################################################

if __name__ == "__main__":

    print("=" * 52)
    print("VED EVENT BUS")
    print("=" * 52)

    bus = EventBus()

    ################################################
    # A listener that works
    ################################################

    def greeter(data):
        print(f"  [greeter] saw {data}")

    ################################################
    # A listener that is broken
    ################################################

    def broken(data):
        raise ValueError("this listener is buggy")

    ################################################
    # A listener that logs everything
    ################################################

    def logger(entry):
        print(f"  [log] {entry['event']}")

    bus.subscribe(Event.FACE_RECOGNISED, broken)
    bus.subscribe(Event.FACE_RECOGNISED, greeter)
    bus.subscribe(WILDCARD, logger)

    print("\nPublishing with a broken listener first:")

    delivered = bus.publish(
        Event.FACE_RECOGNISED,
        {"name": "Pranjal", "score": 0.71}
    )

    print(
        f"\n  {delivered} of 3 listeners succeeded -- "
        "the broken one did not stop the others.\n"
    )

    bus.publish(Event.OBSTACLE, {"distance_cm": 22})

    print(f"\nEvent counts: {bus.stats()}")
    print(f"History: {len(bus.recent())} entries")
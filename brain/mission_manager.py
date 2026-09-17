"""
=========================================================
brain/mission_manager.py

Every multi-step thing Ved does goes through here.

Author: Pranjal

Run from the PROJECT ROOT:
    python3 -m brain.mission_manager

FOUR DESIGN DECISIONS, AND WHY
------------------------------

1. STEPS ARE NON-BLOCKING.

   The obvious way to write "escort a guest" is a
   function with sleeps and while loops. Do that and the
   vision loop stops for the entire escort -- no face
   detection, no obstacle checks, no response to being
   spoken to.

   So every step is a function called once per tick that
   returns RUNNING / DONE / FAILED. Missions advance a
   little each frame and the main loop never blocks.

2. MISSIONS ARE PREEMPTED, NOT KILLED.

   A critical battery has to interrupt a delivery. But
   throwing the delivery away means the towels never
   arrive and nobody knows why. Instead the mission is
   SUSPENDED with its step index intact, the urgent one
   runs, and the original resumes where it left off.

3. THEY SURVIVE A REBOOT.

   A mission is persisted as its NAME plus PARAMS plus
   STEP INDEX -- never as callables, which cannot be
   serialised. On boot the manager rebuilds it from the
   registry. This is the gap flagged repeatedly: a robot
   that loses a delivery to a power cut is not
   deployable.

   Movement missions are deliberately NOT auto-resumed.
   Position is unknown after a restart, so resuming
   navigation would drive blind.

4. UNAVAILABLE MISSIONS ARE REFUSED AT QUEUE TIME.

   Every mission declares what hardware it needs. If the
   chassis does not exist, "deliver medicine" is rejected
   when queued -- not discovered halfway through. Same
   principle as capability enforcement in the
   conversation manager: fail loudly and early, never
   promise something that cannot happen.
=========================================================
"""

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from core.events import Event, event_bus
from core.state import RobotState, RobotTask, state_manager


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MISSION_FILE = DATA_DIR / "missions.json"


####################################################
# Hardware capability flags
#
# Flip these to True as each subsystem lands. Missions
# needing something unavailable are refused at queue
# time with a clear reason.
####################################################

CAPABILITIES = {
    "voice": True,
    "vision": True,
    "face_recognition": True,
    "navigation": False,      # needs chassis + SLAM
    "motors": False,          # needs chassis
    "gripper": False,         # not in V1
    "docking": False,         # needs charging station
    "staff_channel": False,   # needs hotel integration
}


def has(*required):

    return all(CAPABILITIES.get(r, False) for r in required)


def missing(required):

    return [r for r in required if not CAPABILITIES.get(r, False)]


####################################################
# Step results
####################################################

class Status(Enum):

    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    BLOCKED = "blocked"       # can't proceed, try later


class MissionState(Enum):

    QUEUED = "queued"
    RUNNING = "running"
    SUSPENDED = "suspended"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


####################################################
# Priorities
#
# Spaced by 10 so new missions slot in without
# renumbering.
####################################################

class Priority:

    EMERGENCY = 100
    CRITICAL_BATTERY = 90
    MEDICAL = 80
    GUEST_REQUEST = 50
    ESCORT = 45
    DELIVERY = 40
    CHARGE = 30
    PATROL = 10
    IDLE = 0


@dataclass
class Step:
    """
    run(mission) -> Status, called once per tick.

    timeout   seconds before the step is failed
    optional  if True, failure advances instead of
              aborting the whole mission
    """

    name: str
    run: Callable
    timeout: float = 60.0
    optional: bool = False

    started: float = 0.0

    def elapsed(self):

        return time.time() - self.started if self.started else 0.0


@dataclass
class Mission:

    name: str
    steps: list
    priority: int = Priority.GUEST_REQUEST
    params: dict = field(default_factory=dict)
    requires: tuple = ()

    # Movement missions must not silently resume after a
    # power cut -- the robot's position is unknown.
    resumable: bool = True

    max_retries: int = 1

    state: MissionState = MissionState.QUEUED
    step_index: int = 0
    retries: int = 0

    created: float = field(default_factory=time.time)
    started: float = 0.0
    finished: float = 0.0

    error: str = ""

    # Scratch space for steps to share data within a run.
    memory: dict = field(default_factory=dict)

    ####################################################

    def current_step(self):

        if self.step_index < len(self.steps):
            return self.steps[self.step_index]

        return None

    def progress(self):

        if not self.steps:
            return 1.0

        return round(self.step_index / len(self.steps), 2)

    def describe(self):

        step = self.current_step()

        return (
            f"{self.name} "
            f"[{self.step_index + 1}/{len(self.steps)}] "
            f"{step.name if step else 'complete'}"
        )

    def to_dict(self):
        """
        Persisted form. Note it stores the NAME and
        PARAMS, never the step callables -- functions
        cannot be serialised, and rebuilding from the
        registry is what makes resumption possible.
        """

        return {
            "name": self.name,
            "params": self.params,
            "priority": self.priority,
            "state": self.state.value,
            "step_index": self.step_index,
            "retries": self.retries,
            "created": self.created,
            "resumable": self.resumable,
        }


####################################################
# Registry
####################################################

class MissionRegistry:

    def __init__(self):

        self.builders = {}

    def register(self, name, builder):
        """
        builder(**params) -> Mission
        """

        self.builders[name] = builder

        return builder

    def build(self, mission_name, /, **params):

        builder = self.builders.get(mission_name)

        if builder is None:
            return None

        return builder(**params)

    def known(self):

        return sorted(self.builders.keys())


registry = MissionRegistry()


####################################################
# Manager
####################################################

# A challenger must beat the running mission by this much
# to preempt it. Prevents thrashing between two missions
# of near-equal priority.
PREEMPT_MARGIN = 15


class MissionManager:

    def __init__(self, manager=None, persist=True):

        self.state_manager = manager or state_manager

        self.persist = persist

        self.queue = []

        self.current = None

        # Suspended missions, most recent first. A stack,
        # so a delivery interrupted by a charge which is
        # itself interrupted by an emergency unwinds in
        # the right order.
        self.suspended = []

        self.completed = []

        DATA_DIR.mkdir(parents=True, exist_ok=True)

    ####################################################
    # Queueing
    ####################################################

    def can_run(self, mission):
        """
        Returns (ok, reason).
        """

        gaps = missing(mission.requires)

        if gaps:
            return False, (
                f"needs {', '.join(gaps)} -- not available yet"
            )

        return True, None

    ####################################################

    def add(self, mission):
        """
        Queue a mission. Returns (accepted, reason).
        """

        if mission is None:
            return False, "no mission"

        ok, reason = self.can_run(mission)

        if not ok:
            print(f"[MISSION] REFUSED '{mission.name}': {reason}")

            event_bus.publish(
                Event.TASK_FAILED,
                {"mission": mission.name, "reason": reason}
            )

            return False, reason

        mission.state = MissionState.QUEUED

        self.queue.append(mission)

        # Highest priority first; ties broken by age, so
        # an old low-priority mission isn't starved
        # forever by a stream of new equal ones.
        self.queue.sort(key=lambda m: (-m.priority, m.created))

        print(
            f"[MISSION] Queued '{mission.name}' "
            f"(priority {mission.priority})"
        )

        self.save()

        return True, None

    ####################################################

    def request(self, mission_name, /, **params):
        """
        Build from the registry and queue it.

        mission_name is POSITIONAL-ONLY (note the /).
        Otherwise request("greet_guest", name="Pranjal")
        collides -- 'name' is both the mission type and a
        perfectly reasonable mission parameter. This bit
        me immediately in testing.
        """

        mission = registry.build(mission_name, **params)

        if mission is None:
            return False, f"unknown mission '{mission_name}'"

        return self.add(mission)

    ####################################################
    # Control
    ####################################################

    def cancel(self, name=None):
        """
        Cancel the current mission, or a named queued one.
        """

        if name is None:

            if self.current is None:
                return False

            print(f"[MISSION] Cancelled '{self.current.name}'")

            self.current.state = MissionState.CANCELLED
            self.current.finished = time.time()

            self.completed.append(self.current)
            self.current = None

            self.save()

            return True

        before = len(self.queue)

        self.queue = [m for m in self.queue if m.name != name]

        self.save()

        return len(self.queue) < before

    ####################################################

    def clear(self):
        """
        Drop everything. Used on emergency stop.
        """

        for mission in [self.current] + self.queue + self.suspended:

            if mission:
                mission.state = MissionState.CANCELLED

        self.queue.clear()
        self.suspended.clear()
        self.current = None

        self.save()

        print("[MISSION] All missions cleared.")

    ####################################################

    def suspend_current(self, reason=""):

        if self.current is None:
            return False

        self.current.state = MissionState.SUSPENDED

        self.suspended.insert(0, self.current)

        print(
            f"[MISSION] Suspended '{self.current.name}' "
            f"at step {self.current.step_index + 1}"
            + (f" ({reason})" if reason else "")
        )

        self.current = None

        return True

    ####################################################
    # The tick
    ####################################################

    def update(self):
        """
        Advance the current mission by one step-tick.

        Call every loop. Cheap when idle.
        """

        ################################################
        # Emergency clears everything
        ################################################

        if self.state_manager.is_emergency():

            if self.current or self.queue:
                self.clear()

            return None

        ################################################
        # Should something preempt what's running?
        ################################################

        if self.queue:

            challenger = self.queue[0]

            if self.current is None:

                self.current = self.queue.pop(0)

                self._begin(self.current)

            elif challenger.priority > self.current.priority + PREEMPT_MARGIN:

                self.suspend_current(
                    f"preempted by {challenger.name}"
                )

                self.current = self.queue.pop(0)

                self._begin(self.current)

        ################################################
        # Nothing running -- resume anything suspended
        ################################################

        if self.current is None and self.suspended:

            self.current = self.suspended.pop(0)

            self.current.state = MissionState.RUNNING

            print(
                f"[MISSION] Resumed '{self.current.name}' "
                f"at step {self.current.step_index + 1}"
            )

        if self.current is None:
            return None

        ################################################
        # Run one tick of the current step
        ################################################

        mission = self.current

        step = mission.current_step()

        if step is None:
            self._complete(mission)
            return None

        if not step.started:
            step.started = time.time()

        ################################################
        # Timeout
        ################################################

        if step.elapsed() > step.timeout:

            self._step_failed(
                mission, step,
                f"step '{step.name}' timed out after {step.timeout}s"
            )

            return mission

        ################################################
        # Execute
        ################################################

        try:
            status = step.run(mission)

        except Exception as exc:
            self._step_failed(mission, step, f"{step.name}: {exc}")
            return mission

        if status == Status.DONE:

            step.started = 0.0

            mission.step_index += 1

            self.save()

            if mission.step_index >= len(mission.steps):
                self._complete(mission)

        elif status == Status.FAILED:

            self._step_failed(mission, step, f"step '{step.name}' failed")

        # RUNNING and BLOCKED both just wait for the next
        # tick. BLOCKED exists so a step can say "not my
        # turn yet" without burning its timeout... which
        # it does anyway, deliberately: a permanently
        # blocked mission should eventually fail rather
        # than sit forever.

        return mission

    ####################################################

    def _begin(self, mission):

        mission.state = MissionState.RUNNING
        mission.started = time.time()

        print(f"[MISSION] Started '{mission.name}'")

        self.state_manager.set_task(
            RobotTask.DELIVERY
            if "deliver" in mission.name
            else RobotTask.NONE,
            **mission.params
        )

        event_bus.publish(
            Event.TASK_STARTED,
            {"mission": mission.name, "params": mission.params}
        )

        self.save()

    ####################################################

    def _complete(self, mission):

        mission.state = MissionState.DONE
        mission.finished = time.time()

        duration = mission.finished - mission.started

        print(
            f"[MISSION] Completed '{mission.name}' "
            f"in {duration:.1f}s"
        )

        self.completed.append(mission)

        if len(self.completed) > 50:
            self.completed.pop(0)

        self.current = None

        self.state_manager.clear_task()

        event_bus.publish(
            Event.TASK_COMPLETE,
            {"mission": mission.name, "duration": round(duration, 1)}
        )

        self.save()

    ####################################################

    def _step_failed(self, mission, step, error):

        ################################################
        # Optional steps don't sink the mission
        ################################################

        if step.optional:

            print(f"[MISSION] Skipped optional step: {error}")

            step.started = 0.0
            mission.step_index += 1

            return

        ################################################
        # Retry from the current step
        ################################################

        if mission.retries < mission.max_retries:

            mission.retries += 1

            step.started = 0.0

            print(
                f"[MISSION] Retry {mission.retries}"
                f"/{mission.max_retries} of '{step.name}'"
            )

            return

        ################################################
        # Give up
        ################################################

        mission.state = MissionState.FAILED
        mission.error = error
        mission.finished = time.time()

        print(f"[MISSION] FAILED '{mission.name}': {error}")

        self.completed.append(mission)

        self.current = None

        self.state_manager.clear_task()

        event_bus.publish(
            Event.TASK_FAILED,
            {"mission": mission.name, "reason": error}
        )

        self.save()

    ####################################################
    # Status
    ####################################################

    def status(self):

        return {
            "current": (
                self.current.describe() if self.current else None
            ),
            "progress": (
                self.current.progress() if self.current else None
            ),
            "queued": [m.name for m in self.queue],
            "suspended": [m.name for m in self.suspended],
        }

    def busy(self):

        return self.current is not None

    ####################################################
    # Persistence
    ####################################################

    def save(self):

        if not self.persist:
            return False

        try:
            data = {
                "saved_at": time.time(),
                "current": (
                    self.current.to_dict() if self.current else None
                ),
                "queue": [m.to_dict() for m in self.queue],
                "suspended": [m.to_dict() for m in self.suspended],
            }

            tmp = MISSION_FILE.with_suffix(".tmp")

            with open(tmp, "w") as f:
                json.dump(data, f, indent=2)

            tmp.replace(MISSION_FILE)

            return True

        except Exception as exc:
            print(f"[MISSION] Could not save: {exc}")
            return False

    ####################################################

    def restore(self):
        """
        Rebuild missions from disk after a restart.

        Returns a summary of what was recovered and what
        was deliberately dropped.
        """

        if not MISSION_FILE.exists():
            return {"restored": [], "dropped": []}

        try:
            with open(MISSION_FILE) as f:
                data = json.load(f)

        except Exception as exc:
            print(f"[MISSION] Could not load: {exc}")
            return {"restored": [], "dropped": []}

        restored = []
        dropped = []

        entries = []

        if data.get("current"):
            entries.append(data["current"])

        entries += data.get("suspended", [])
        entries += data.get("queue", [])

        for entry in entries:

            name = entry.get("name")

            ############################################
            # Movement missions are NOT auto-resumed.
            # Position is unknown after a restart.
            ############################################

            if not entry.get("resumable", True):
                dropped.append((name, "not safe to resume"))
                continue

            mission = registry.build(name, **(entry.get("params") or {}))

            if mission is None:
                dropped.append((name, "unknown mission type"))
                continue

            ok, reason = self.can_run(mission)

            if not ok:
                dropped.append((name, reason))
                continue

            # Pick up where it stopped.
            mission.step_index = min(
                entry.get("step_index", 0),
                len(mission.steps)
            )

            mission.retries = entry.get("retries", 0)

            self.queue.append(mission)

            restored.append(f"{name} (step {mission.step_index + 1})")

        self.queue.sort(key=lambda m: (-m.priority, m.created))

        if restored:
            print(f"[MISSION] Restored: {', '.join(restored)}")

        for name, reason in dropped:
            print(f"[MISSION] Dropped '{name}': {reason}")

        self.save()

        return {"restored": restored, "dropped": dropped}


####################################################
# Step helpers
####################################################

def say(text, language="English"):
    """A step that speaks once, then completes."""

    def run(mission):

        # Format OUTSIDE the try. Doing it inside means
        # the fallback print gets the raw template --
        # "Hello {name}." out loud, which is worse than
        # saying nothing.
        try:
            spoken = text.format(**mission.params)
        except (KeyError, IndexError):
            spoken = text

        try:
            from core.speech import speak
            speak(spoken, language)
        except Exception:
            print(f"[VED] {spoken}")

        return Status.DONE

    return run


def wait(seconds):
    """A step that waits without blocking the loop."""

    def run(mission):

        key = f"_wait_{id(run)}"

        if key not in mission.memory:
            mission.memory[key] = time.time()

        if time.time() - mission.memory[key] >= seconds:
            del mission.memory[key]
            return Status.DONE

        return Status.RUNNING

    return run


def stub(label, ticks=3):
    """
    Placeholder for a step that needs hardware.

    Completes after a few ticks so mission flow can be
    tested end to end before the chassis exists.
    """

    def run(mission):

        key = f"_stub_{label}"

        mission.memory[key] = mission.memory.get(key, 0) + 1

        if mission.memory[key] >= ticks:
            del mission.memory[key]
            return Status.DONE

        return Status.RUNNING

    return run


####################################################
# Mission definitions
####################################################

def build_greet_guest(name="guest", language="English"):

    return Mission(
        name="greet_guest",
        priority=Priority.GUEST_REQUEST,
        params={"name": name},
        requires=("voice",),
        steps=[
            Step("greet", say("Hello {name}.", language)),
            Step("pause", wait(1.0)),
        ],
    )


def build_charge():

    return Mission(
        name="charge",
        priority=Priority.CHARGE,
        requires=("navigation", "docking"),
        resumable=False,
        steps=[
            Step("find_dock", stub("find_dock"), timeout=60),
            Step("navigate_to_dock", stub("nav_dock"), timeout=120),
            Step("align", stub("align"), timeout=30),
            Step("connect", stub("connect"), timeout=20),
        ],
    )


def build_escort_guest(room="", language="English"):

    return Mission(
        name="escort_guest",
        priority=Priority.ESCORT,
        params={"room": room},
        requires=("navigation", "motors", "voice"),
        resumable=False,
        steps=[
            # VERIFY BEFORE PROMISING.
            #
            # The obvious order is to confirm first and
            # plan second, because that's the order the
            # conversation happens in. But if planning
            # then fails, Ved has already told the guest
            # it would take them somewhere -- the exact
            # broken promise the conversation manager
            # refuses to make.
            #
            # So: plan silently, and only speak once the
            # route is known to exist.
            Step("plan_route", stub("plan"), timeout=15),
            Step("confirm", say("I'll take you to room {room}.", language)),
            Step("lead", stub("lead"), timeout=300),
            Step("check_following", stub("check"), optional=True),
            Step("arrive", say("Here is room {room}.", language)),
        ],
    )


def build_deliver_item(item="", room="", language="English"):

    return Mission(
        name="deliver_item",
        priority=Priority.DELIVERY,
        params={"item": item, "room": room},
        requires=("navigation", "motors"),
        resumable=False,
        steps=[
            # Nothing is announced until Ved has actually
            # arrived. Announcing at the start means a
            # failed delivery is one the guest was told
            # about and never received.
            Step("load", stub("load"), timeout=120),
            Step("navigate", stub("nav"), timeout=300),
            Step("announce", say("Delivery for room {room}.", language)),
            Step("await_pickup", stub("pickup"), timeout=120),
            Step("return", stub("return"), timeout=300),
        ],
    )


def build_deliver_medicine(patient="", room="", language="English"):

    mission = build_deliver_item(item="medicine", room=room, language=language)

    mission.name = "deliver_medicine"

    # Medicine outranks towels. Obvious once stated,
    # easy to forget when everything is "a delivery".
    mission.priority = Priority.MEDICAL
    mission.params["patient"] = patient
    mission.max_retries = 2

    return mission


def build_find_person(name="", language="English"):

    return Mission(
        name="find_person",
        priority=Priority.GUEST_REQUEST,
        params={"name": name},
        requires=("vision", "face_recognition", "navigation"),
        resumable=False,
        steps=[
            Step("scan_here", stub("scan"), timeout=20),
            Step("search_area", stub("search"), timeout=180),
            Step("announce", say("I found {name}.", language)),
        ],
    )


def build_patrol(route=""):

    return Mission(
        name="patrol",
        priority=Priority.PATROL,
        params={"route": route},
        requires=("navigation", "motors"),
        resumable=False,
        steps=[
            Step("next_waypoint", stub("waypoint"), timeout=120),
            Step("observe", stub("observe"), timeout=30),
        ],
    )


def build_return_home():

    return Mission(
        name="return_home",
        priority=Priority.CHARGE,
        requires=("navigation", "motors"),
        resumable=False,
        steps=[
            Step("navigate_home", stub("home"), timeout=300),
        ],
    )


####################################################
# Register everything
####################################################

registry.register("greet_guest", build_greet_guest)
registry.register("charge", build_charge)
registry.register("escort_guest", build_escort_guest)
registry.register("deliver_item", build_deliver_item)
registry.register("deliver_medicine", build_deliver_medicine)
registry.register("find_person", build_find_person)
registry.register("patrol", build_patrol)
registry.register("return_home", build_return_home)


####################################################
# Singleton
####################################################

mission_manager = MissionManager()


####################################################

if __name__ == "__main__":

    print("=" * 58)
    print("VED MISSION MANAGER")
    print("=" * 58)

    manager = MissionManager(persist=False)

    ################################################
    # Capability gating
    ################################################

    print("\n--- What can actually be queued today ---\n")

    for name in registry.known():

        mission = registry.build(name)

        ok, reason = manager.can_run(mission)

        print(
            f"  {name:<18} "
            + ("OK" if ok else f"REFUSED -- {reason}")
        )

    ################################################
    # A mission that can run
    ################################################

    print("\n--- Running a mission, one tick at a time ---\n")

    manager.request("greet_guest", name="Pranjal")

    # Ticks are deliberately slower than real, so the
    # 1-second wait step actually elapses. In the live
    # loop this runs at frame rate and the mission
    # advances across many ticks -- which is the point:
    # nothing blocks.
    for tick in range(8):

        manager.update()

        status = manager.status()

        print(f"  tick {tick}: {status['current'] or 'idle'}")

        time.sleep(0.2)

    ################################################
    # Preemption
    ################################################

    print("\n--- Preemption: medicine interrupts a greeting ---\n")

    CAPABILITIES["navigation"] = True
    CAPABILITIES["motors"] = True

    manager2 = MissionManager(persist=False)

    manager2.request("escort_guest", room="204")

    manager2.update()
    manager2.update()

    print(f"  running    : {manager2.status()['current']}")

    manager2.request("deliver_medicine", patient="Mrs Shah", room="309")

    manager2.update()

    print(f"  after page : {manager2.status()['current']}")
    print(f"  suspended  : {manager2.status()['suspended']}")

    ################################################
    # Emergency
    ################################################

    print("\n--- Emergency clears everything ---\n")

    state_manager.emergency_stop("obstacle")

    manager2.update()

    print(f"  current    : {manager2.status()['current']}")
    print(f"  queued     : {manager2.status()['queued']}")

    state_manager.clear_emergency()

    CAPABILITIES["navigation"] = False
    CAPABILITIES["motors"] = False
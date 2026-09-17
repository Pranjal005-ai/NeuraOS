"""
=========================================================
vision/scheduler.py

Frame budget dispatcher for Ved's vision stack.

Author: Pranjal

THE PROBLEM
-----------
A Pi 5 cannot run face recognition, YOLO, pose, QR and
OCR on every frame. Rough per-frame costs on a Pi 5 CPU:

    motion diff        ~2ms
    Haar face gate     ~3ms
    InsightFace        ~80ms
    YOLOv8n            ~120ms
    QR detect          ~15ms
    EasyOCR            ~5000ms+

Run them all per frame and you get under 2fps, every
feature starved, and no way to tell which one is at
fault. Worse, each new feature silently slows every
existing one -- so you end up debugging framerate
instead of behaviour.

THE APPROACH
------------
Every consumer declares how often it wants to run and
how important it is. The scheduler:

  - runs each at its own interval, not every frame
  - runs at most one EXPENSIVE task per frame, so a
    single tick never stacks 80ms + 120ms + 15ms
  - lets a cheap gate suppress an expensive task
    (no motion -> don't run recognition)
  - measures actual cost and reports it, so you can see
    where the time went instead of guessing

Priority breaks ties when several are due at once.
Higher runs first.
=========================================================
"""

import time
from dataclasses import dataclass, field
from typing import Callable, Optional


####################################################
# Cost classes
####################################################

CHEAP = "cheap"          # < 10ms   -- can run every frame
MODERATE = "moderate"    # 10-50ms  -- a few per second
EXPENSIVE = "expensive"  # > 50ms   -- one per frame, max


@dataclass
class Task:
    """
    One vision consumer.

    name      identifier, used in reports
    run       callable taking the frame, returning anything
    interval  minimum seconds between runs
    cost      CHEAP / MODERATE / EXPENSIVE
    priority  higher wins when several are due
    gate      optional callable(scheduler) -> bool.
              Return False to skip this tick.
    enabled   toggle without unregistering
    """

    name: str
    run: Callable
    interval: float = 0.2
    cost: str = MODERATE
    priority: int = 0
    gate: Optional[Callable] = None
    enabled: bool = True

    last_run: float = 0.0
    last_result: object = None
    runs: int = 0
    skips: int = 0
    total_time: float = 0.0
    max_time: float = 0.0
    errors: int = 0

    def due(self, now):

        return self.enabled and (now - self.last_run) >= self.interval

    def average_ms(self):

        if not self.runs:
            return 0.0

        return (self.total_time / self.runs) * 1000.0


class VisionScheduler:

    def __init__(self, expensive_per_frame=1):

        self.tasks = {}

        # How many EXPENSIVE tasks may run in one tick.
        # 1 is the right default: two 80ms+ tasks in one
        # frame is a visible stutter.
        self.expensive_per_frame = expensive_per_frame

        self.frames = 0
        self.started = time.time()

        self._frame_times = []

    ####################################################

    def add(self, task):

        self.tasks[task.name] = task

        return task

    def register(
        self,
        name,
        run,
        interval=0.2,
        cost=MODERATE,
        priority=0,
        gate=None
    ):

        return self.add(
            Task(
                name=name,
                run=run,
                interval=interval,
                cost=cost,
                priority=priority,
                gate=gate
            )
        )

    ####################################################

    def enable(self, name, enabled=True):

        if name in self.tasks:
            self.tasks[name].enabled = enabled
            return True

        return False

    def disable(self, name):

        return self.enable(name, False)

    def result(self, name):
        """
        Most recent result from a task. Lets consumers
        read each other's output without re-running it --
        the greeter can use the detector's faces rather
        than detecting again.
        """

        task = self.tasks.get(name)

        return task.last_result if task else None

    def age_of(self, name):
        """
        Seconds since a task last produced a result.
        Useful for deciding whether cached output is
        still trustworthy.
        """

        task = self.tasks.get(name)

        if task is None or not task.runs:
            return None

        return time.time() - task.last_run

    ####################################################

    def tick(self, frame):
        """
        Run whatever is due for this frame.

        Returns {name: result} for tasks that ran.
        """

        if frame is None:
            return {}

        now = time.time()

        self.frames += 1

        ################################################
        # Who wants to run?
        ################################################

        due = [t for t in self.tasks.values() if t.due(now)]

        # Highest priority first, then cheapest. Cheap
        # gates therefore run BEFORE the expensive tasks
        # they might suppress -- which is the whole point
        # of having gates.
        cost_order = {CHEAP: 0, MODERATE: 1, EXPENSIVE: 2}

        due.sort(
            key=lambda t: (-t.priority, cost_order.get(t.cost, 1))
        )

        results = {}

        expensive_used = 0

        frame_start = time.perf_counter()

        for task in due:

            ############################################
            # Budget: one expensive task per frame
            ############################################

            if task.cost == EXPENSIVE:

                if expensive_used >= self.expensive_per_frame:
                    task.skips += 1
                    continue

            ############################################
            # Gate
            ############################################

            if task.gate is not None:

                try:
                    if not task.gate(self):
                        task.skips += 1
                        task.last_run = now
                        continue

                except Exception as exc:
                    print(f"[SCHED] Gate '{task.name}' failed: {exc}")
                    task.skips += 1
                    continue

            ############################################
            # Run
            ############################################

            started = time.perf_counter()

            try:
                task.last_result = task.run(frame)
                results[task.name] = task.last_result

            except Exception as exc:
                # One failing task must not stop the rest.
                task.errors += 1
                print(f"[SCHED] Task '{task.name}' failed: {exc}")

            elapsed = time.perf_counter() - started

            task.last_run = time.time()
            task.runs += 1
            task.total_time += elapsed
            task.max_time = max(task.max_time, elapsed)

            if task.cost == EXPENSIVE:
                expensive_used += 1

        frame_elapsed = time.perf_counter() - frame_start

        self._frame_times.append(frame_elapsed)

        if len(self._frame_times) > 120:
            self._frame_times.pop(0)

        return results

    ####################################################

    def frame_budget_ms(self):
        """Average time spent in tick(), in ms."""

        if not self._frame_times:
            return 0.0

        return (
            sum(self._frame_times) / len(self._frame_times)
        ) * 1000.0

    ####################################################

    def report(self):
        """
        Where the time actually went.

        Print this when the loop feels slow, instead of
        guessing which model is to blame.
        """

        uptime = time.time() - self.started

        lines = [
            "",
            "=" * 62,
            f"VISION SCHEDULER  --  {self.frames} frames "
            f"in {uptime:.0f}s "
            f"({self.frames / max(uptime, 0.001):.1f} fps)",
            f"Average tick: {self.frame_budget_ms():.1f}ms",
            "=" * 62,
            f"{'task':<18}{'cost':<11}{'runs':>6}"
            f"{'skips':>7}{'avg ms':>9}{'max ms':>9}",
            "-" * 62,
        ]

        for task in sorted(
            self.tasks.values(),
            key=lambda t: -t.total_time
        ):

            flag = "" if task.enabled else "  (off)"

            lines.append(
                f"{task.name:<18}{task.cost:<11}"
                f"{task.runs:>6}{task.skips:>7}"
                f"{task.average_ms():>9.1f}"
                f"{task.max_time * 1000:>9.1f}{flag}"
            )

            if task.errors:
                lines.append(f"{'':>18}  {task.errors} error(s)")

        lines.append("=" * 62)

        return "\n".join(lines)


####################################################
# Ready-made gates
####################################################

def motion_gate(threshold=0.0025):
    """
    Suppress expensive work when nothing is moving.

    This is the single highest-value optimisation in the
    whole stack: an empty corridor costs 2ms a frame
    instead of 200ms, which is what makes running several
    features at once affordable at all.
    """

    import cv2
    import numpy as np

    state = {"previous": None}

    def detect(frame):

        small = cv2.resize(frame, (160, 120))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        previous = state["previous"]

        state["previous"] = gray

        if previous is None:
            return {"moving": True, "amount": 1.0}

        diff = cv2.absdiff(gray, previous)

        amount = float(np.count_nonzero(diff > 20)) / diff.size

        return {
            "moving": amount > threshold,
            "amount": round(amount, 5),
        }

    return detect


def requires_motion(scheduler, motion_task="motion", grace=2.0):
    """
    Gate factory: only run if motion was seen recently.

    The grace period matters -- someone standing still to
    talk to Ved produces no motion, and cutting
    recognition the moment they stop moving would be
    exactly wrong.
    """

    last_motion = {"at": 0.0}

    def gate(sched):

        result = sched.result(motion_task)

        if result and result.get("moving"):
            last_motion["at"] = time.time()
            return True

        return (time.time() - last_motion["at"]) < grace

    return gate


####################################################

if __name__ == "__main__":

    import numpy as np

    print("Simulating a scheduler tick pattern.\n")

    sched = VisionScheduler()

    def fake(name, ms):

        def run(frame):
            time.sleep(ms / 1000.0)
            return f"{name}-result"

        return run

    sched.register(
        "motion", fake("motion", 2),
        interval=0.0, cost=CHEAP, priority=10
    )

    sched.register(
        "face", fake("face", 80),
        interval=0.2, cost=EXPENSIVE, priority=5,
        gate=requires_motion(sched)
    )

    sched.register(
        "yolo", fake("yolo", 120),
        interval=1.0, cost=EXPENSIVE, priority=1
    )

    sched.register(
        "qr", fake("qr", 15),
        interval=0.5, cost=MODERATE, priority=2
    )

    frame = np.zeros((480, 640, 3), np.uint8)

    # Motion always true in this simulation.
    sched.tasks["motion"].run = lambda f: {"moving": True}

    start = time.time()

    while time.time() - start < 3.0:
        sched.tick(frame)
        time.sleep(0.01)

    print(sched.report())

    print(
        "\nNote: face and yolo are both EXPENSIVE, so they "
        "\nnever run in the same tick -- see the skip counts."
    )
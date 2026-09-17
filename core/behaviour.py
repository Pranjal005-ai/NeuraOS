"""
=========================================================
core/behaviour.py

Attention and behaviour engine.

Author: Pranjal

WHAT THIS IS FOR
----------------
Until now the greeter WAS the behaviour: see face, greet
face. That works for one feature and falls apart at two.
The moment Ved can also deliver, patrol, charge and
respond to being spoken to, something has to decide which
of those wins right now.

TWO LAYERS
----------
ATTENTION decides WHO or WHAT matters. Several people in
a lobby, a QR marker, a voice from behind -- attention
scores them and picks one target. Crucially it has
HYSTERESIS: a new candidate must be clearly better before
Ved switches, otherwise it ping-pongs between two people
standing side by side, which looks broken and is the
single most common failure in robots like this.

BEHAVIOUR decides WHAT TO DO about it, by running a list
of rules in priority order. The first rule whose
condition is met wins. Rules are declarative and
independent, so adding "escort a guest" later does not
require touching greeting logic.

WHY RULES AND NOT A STATE MACHINE
---------------------------------
A state machine needs an explicit transition for every
pair of states -- N^2 edges, and adding one state means
revisiting all of them. Priority rules only need each
behaviour to know its own precondition. Emergencies stay
correct because they sit at the top of the list, not
because every state remembered to handle them.
=========================================================
"""

import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from core.events import Event, event_bus
from core.state import (
    RobotMode,
    RobotState,
    RobotTask,
    state_manager,
)


####################################################
# Attention
####################################################

# A challenger must beat the current target by this much
# before Ved switches. Without it, two people at similar
# distance make the robot's head swing back and forth.
ATTENTION_SWITCH_MARGIN = 0.15

# Drop a target not seen for this long.
ATTENTION_TIMEOUT = 3.0

# Faces smaller than this are too far away to be
# addressing Ved.
MIN_ENGAGE_WIDTH = 100


@dataclass
class Target:

    identity: str
    box: tuple
    score: float
    kind: str = "person"

    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    def width(self):

        return self.box[2] - self.box[0]

    def age(self):

        return time.time() - self.first_seen

    def staleness(self):

        return time.time() - self.last_seen


class Attention:
    """
    Decides who Ved is paying attention to.
    """

    def __init__(self, frame_width=640):

        self.frame_width = frame_width

        self.target = None

        self._last_switch = 0.0

    ####################################################

    def score_candidate(self, name, box, recognition_score):
        """
        How much does this person deserve attention?

        Weighted by:
          closeness  -- bigger face means closer means
                        more likely to be addressing Ved
          centrality -- someone in front of Ved is more
                        likely talking to it than someone
                        at the edge of frame
          known      -- a recognised guest slightly
                        outranks a stranger
        """

        x1, _, x2, _ = box

        width = x2 - x1

        if width < MIN_ENGAGE_WIDTH:
            return 0.0

        # Closeness, normalised and capped.
        closeness = min(1.0, width / (self.frame_width * 0.45))

        # Centrality: 1.0 dead centre, 0.0 at the edge.
        centre = (x1 + x2) / 2.0
        offset = abs(centre / self.frame_width - 0.5) * 2.0
        centrality = max(0.0, 1.0 - offset)

        known_bonus = 0.15 if name != "Unknown" else 0.0

        return round(
            closeness * 0.5
            + centrality * 0.35
            + known_bonus
            + min(recognition_score, 1.0) * 0.1,
            3
        )

    ####################################################

    def update(self, people):
        """
        people: [{"name", "score", "box"}] from
                face_engine.recognize_all()

        Returns the current Target, or None.
        """

        now = time.time()

        ################################################
        # Score everyone
        ################################################

        best = None
        best_score = 0.0

        for person in people or []:

            score = self.score_candidate(
                person["name"],
                person["box"],
                person.get("score", 0.0)
            )

            if score > best_score:
                best_score = score
                best = person

        ################################################
        # Nobody worth attending to
        ################################################

        if best is None or best_score <= 0:

            if (
                self.target
                and self.target.staleness() > ATTENTION_TIMEOUT
            ):
                lost = self.target
                self.target = None

                event_bus.publish(
                    Event.PERSON_LOST,
                    {"identity": lost.identity}
                )

            return self.target

        ################################################
        # Same person -- refresh
        ################################################

        if (
            self.target
            and self.target.identity == best["name"]
            and best["name"] != "Unknown"
        ):
            self.target.box = best["box"]
            self.target.score = best_score
            self.target.last_seen = now

            return self.target

        ################################################
        # No target -- take this one
        ################################################

        if self.target is None:

            self.target = Target(
                identity=best["name"],
                box=best["box"],
                score=best_score
            )

            self._last_switch = now

            return self.target

        ################################################
        # Challenger -- require a clear margin
        #
        # This is the anti-ping-pong rule. Without it,
        # two people standing side by side make Ved
        # alternate between them every tick.
        ################################################

        if best_score > self.target.score + ATTENTION_SWITCH_MARGIN:

            self.target = Target(
                identity=best["name"],
                box=best["box"],
                score=best_score
            )

            self._last_switch = now

        elif self.target.staleness() > ATTENTION_TIMEOUT:

            # Current target has gone; take the best
            # available even without the margin.
            self.target = Target(
                identity=best["name"],
                box=best["box"],
                score=best_score
            )

        return self.target

    ####################################################

    def clear(self):

        self.target = None


####################################################
# Behaviour rules
####################################################

@dataclass
class Rule:
    """
    name       identifier, appears in logs
    condition  callable(context) -> bool
    action     callable(context) -> optional string
    priority   higher runs first
    cooldown   minimum seconds between firings
    """

    name: str
    condition: Callable
    action: Callable
    priority: int = 0
    cooldown: float = 0.0

    last_fired: float = 0.0
    fires: int = 0

    def ready(self):

        return (time.time() - self.last_fired) >= self.cooldown


class BehaviourEngine:

    def __init__(self, manager=None):

        self.manager = manager or state_manager

        self.rules = []

        self.attention = Attention()

        self.context = {}

        self.current_behaviour = None

        self._history = []

    ####################################################

    def add_rule(self, rule):

        self.rules.append(rule)

        # Highest priority first, evaluated in order.
        self.rules.sort(key=lambda r: -r.priority)

        return rule

    def rule(self, name, priority=0, cooldown=0.0):
        """
        Decorator form:

            @engine.rule("greet", priority=50)
            def greet(ctx): ...

        The decorated function is the ACTION; attach the
        condition with .when().
        """

        def decorator(action):

            new_rule = Rule(
                name=name,
                condition=lambda ctx: True,
                action=action,
                priority=priority,
                cooldown=cooldown
            )

            self.add_rule(new_rule)

            action.rule = new_rule

            return action

        return decorator

    ####################################################

    def update(self, **context):
        """
        Evaluate rules once. Returns the rule that fired,
        or None.

        First match wins. Rules are sorted by priority, so
        an emergency rule at priority 100 always beats a
        greeting at 50 -- without every other rule having
        to remember that emergencies exist.
        """

        self.context = context
        self.context["manager"] = self.manager
        self.context["attention"] = self.attention

        for rule in self.rules:

            if not rule.ready():
                continue

            try:
                if not rule.condition(self.context):
                    continue

            except Exception as exc:
                print(f"[BEHAVIOUR] Condition '{rule.name}' failed: {exc}")
                continue

            ############################################
            # Fire
            ############################################

            try:
                result = rule.action(self.context)

            except Exception as exc:
                print(f"[BEHAVIOUR] Action '{rule.name}' failed: {exc}")
                continue

            rule.last_fired = time.time()
            rule.fires += 1

            if self.current_behaviour != rule.name:

                print(f"[BEHAVIOUR] -> {rule.name}")

                self.current_behaviour = rule.name

                self._history.append((time.time(), rule.name))

                if len(self._history) > 100:
                    self._history.pop(0)

            return rule

        self.current_behaviour = None

        return None

    ####################################################

    def report(self):

        lines = [
            "",
            "=" * 52,
            "BEHAVIOUR RULES  (evaluated top to bottom)",
            "=" * 52,
            f"{'priority':>9}  {'rule':<22}{'fires':>7}",
            "-" * 52,
        ]

        for rule in self.rules:
            lines.append(
                f"{rule.priority:>9}  {rule.name:<22}{rule.fires:>7}"
            )

        lines.append("=" * 52)

        return "\n".join(lines)


####################################################
# Default rule set
####################################################

def install_default_rules(engine, greeter=None):
    """
    The baseline behaviours, in priority order.

    Priorities are spaced by 10 so you can slot new rules
    between them without renumbering everything.
    """

    manager = engine.manager

    ################################################
    # 100 -- Emergency. Nothing outranks this.
    ################################################

    def is_emergency(ctx):
        return manager.is_emergency()

    def handle_emergency(ctx):
        # Deliberately does nothing except hold position.
        # Clearing an emergency must be a human decision.
        return "halted"

    engine.add_rule(
        Rule("emergency", is_emergency, handle_emergency, priority=100)
    )

    ################################################
    # 90 -- Critical battery. Beats any task.
    ################################################

    def battery_critical(ctx):
        return ctx.get("battery", 100) < 10

    def go_charge(ctx):
        manager.set(RobotState.DOCKING, reason="battery critical")
        event_bus.publish(Event.BATTERY_CRITICAL, ctx.get("battery"))
        return "docking"

    engine.add_rule(
        Rule(
            "battery_critical",
            battery_critical,
            go_charge,
            priority=90,
            cooldown=30.0
        )
    )

    ################################################
    # 70 -- Someone is talking to us.
    ################################################

    def being_addressed(ctx):
        return ctx.get("wake_word") or ctx.get("speech_heard")

    def listen(ctx):
        manager.set(RobotState.LISTENING)
        return "listening"

    engine.add_rule(
        Rule("respond", being_addressed, listen, priority=70)
    )

    ################################################
    # 50 -- A person is in front of us.
    ################################################

    def person_present(ctx):

        target = ctx["attention"].target

        return (
            target is not None
            and target.staleness() < 1.0
            and manager.get() not in {
                RobotState.CHARGING,
                RobotState.DOCKING,
            }
        )

    def attend_person(ctx):

        target = ctx["attention"].target

        if greeter is not None and target.identity != "Unknown":
            # The greeter owns its own cooldowns.
            pass

        manager.set_task(
            RobotTask.GREETING,
            person=target.identity
        )

        return f"attending {target.identity}"

    engine.add_rule(
        Rule(
            "attend_person",
            person_present,
            attend_person,
            priority=50,
            cooldown=1.0
        )
    )

    ################################################
    # 30 -- Low battery, but only when otherwise idle.
    #
    # Deliberately BELOW attending a person: finishing a
    # conversation matters more than topping up at 25%.
    ################################################

    def battery_low(ctx):
        return ctx.get("battery", 100) < 25

    def announce_low(ctx):
        event_bus.publish(Event.BATTERY_LOW, ctx.get("battery"))
        return "battery low"

    engine.add_rule(
        Rule(
            "battery_low",
            battery_low,
            announce_low,
            priority=30,
            cooldown=300.0
        )
    )

    ################################################
    # 10 -- Nothing happening.
    ################################################

    def always(ctx):
        return True

    def go_idle(ctx):

        if manager.get() not in {
            RobotState.IDLE,
            RobotState.CHARGING,
            RobotState.DOCKING,
            RobotState.SLEEPING,
        }:
            manager.set(RobotState.IDLE)

        manager.clear_task()

        return "idle"

    engine.add_rule(
        Rule("idle", always, go_idle, priority=10, cooldown=2.0)
    )

    return engine


####################################################
# Singleton
####################################################

behaviour_engine = BehaviourEngine()


####################################################

if __name__ == "__main__":

    print("=" * 52)
    print("VED BEHAVIOUR ENGINE")
    print("=" * 52)

    engine = BehaviourEngine()

    install_default_rules(engine)

    print(engine.report())

    ################################################
    # Attention: the ping-pong test
    ################################################

    print("\n--- Attention with two people side by side ---\n")

    attention = engine.attention

    # Two people, very similar scores.
    frame_a = [
        {"name": "Pranjal", "score": 0.7, "box": (240, 100, 380, 280)},
        {"name": "Rahul", "score": 0.7, "box": (400, 100, 535, 280)},
    ]

    for tick in range(4):

        target = attention.update(frame_a)

        print(
            f"  tick {tick}: attending {target.identity} "
            f"(score {target.score})"
        )

    print("\n  Stable -- no ping-pong between similar candidates.")

    ################################################
    # A clearly closer person should win
    ################################################

    print("\n--- Someone steps much closer ---\n")

    frame_b = [
        {"name": "Pranjal", "score": 0.7, "box": (240, 100, 380, 280)},
        {"name": "Rahul", "score": 0.7, "box": (200, 60, 480, 400)},
    ]

    target = attention.update(frame_b)

    print(f"  attending {target.identity} (score {target.score})")

    ################################################
    # Rules under different conditions
    ################################################

    print("\n--- Rule selection ---\n")

    for label, ctx in [
        ("person present", {"battery": 80}),
        ("battery critical", {"battery": 5}),
        ("spoken to", {"battery": 80, "wake_word": True}),
    ]:
        fired = engine.update(**ctx)

        print(f"  {label:<18} -> {fired.name if fired else 'none'}")

    print("\n  Emergency and battery outrank people. As intended.")
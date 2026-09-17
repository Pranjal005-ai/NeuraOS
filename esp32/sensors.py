"""
=========================================================
esp32/sensors.py

Sensor readings from the ESP32.

Author: Pranjal

WHAT CHANGED
------------
The old version was one line: return esp32.read().

Three problems with that:

1. It returned None whenever no new line had arrived --
   which is most calls, since the control loop runs far
   faster than sensor updates. Callers saw None and had
   to decide whether that meant "no board" or "nothing
   new yet". Those need different responses.

2. It returned the OLDEST buffered line, not the newest.
   With readings arriving faster than they're consumed,
   the buffer grows and the distances you act on get
   progressively more out of date. For obstacle
   avoidance that is actively dangerous.

3. No staleness check. A dead link looked identical to
   a clear corridor, because both produce "no obstacle".

Now: the latest reading is cached, its age is tracked,
and callers can ask whether the data is fresh enough to
trust before driving on it.
=========================================================
"""

import time

from .esp32 import esp32


# Readings older than this should not be trusted for
# anything involving movement.
STALE_AFTER = 1.0

EXPECTED_KEYS = ("front", "left", "right")


class SensorCache:

    def __init__(self):

        self.data = {}
        self.updated = 0.0

        self.reads = 0
        self.errors = 0

    ####################################################

    def poll(self):
        """
        Drain the serial buffer, keep the newest reading.

        Call this once per control loop.
        """

        latest = esp32.read_latest()

        if latest is None:
            return self.data or None

        ################################################
        # Plain text is a boot or debug message, not a
        # reading. Don't let it overwrite good data.
        ################################################

        if not isinstance(latest, dict):
            return self.data or None

        self.data = latest
        self.updated = time.time()
        self.reads += 1

        return self.data

    ####################################################

    def age(self):
        """Seconds since the last real reading."""

        if not self.updated:
            return None

        return time.time() - self.updated

    ####################################################

    def fresh(self, max_age=STALE_AFTER):
        """
        Is the data recent enough to drive on?

        Ask this before acting on a distance. A dead link
        and a clear corridor both look like "no obstacle"
        otherwise.
        """

        age = self.age()

        return age is not None and age <= max_age

    ####################################################

    def get(self, key, default=None):

        return self.data.get(key, default)

    ####################################################

    def distances(self):
        """
        {front, left, right} in cm, None where unknown.

        Returns all None when the link is dead, so the
        navigator's existing None handling applies with
        no special case.
        """

        if not self.fresh():
            return {key: None for key in EXPECTED_KEYS}

        return {
            key: self.data.get(key)
            for key in EXPECTED_KEYS
        }

    ####################################################

    def status(self):

        return {
            "connected": esp32.connected(),
            "port": esp32.port,
            "fresh": self.fresh(),
            "age": (
                round(self.age(), 2)
                if self.age() is not None else None
            ),
            "reads": self.reads,
        }


####################################################
# Singleton
####################################################

_cache = SensorCache()


def getSensors():
    """
    Latest sensor reading, or None.

    Kept for compatibility -- robot_manager and the
    navigator already call this name.
    """

    return _cache.poll()


def getDistances():
    """
    {front, left, right} in cm, with staleness applied.
    """

    _cache.poll()

    return _cache.distances()


def sensorsFresh(max_age=STALE_AFTER):

    return _cache.fresh(max_age)


def sensorStatus():

    return _cache.status()


def getBattery():
    """
    Battery percentage, or None.

    The UPS HAT isn't wired to the ESP32 yet -- this
    exists so behaviour.py and main.py can call it now
    and get a real number later without changing.
    """

    _cache.poll()

    return _cache.get("battery")


####################################################

if __name__ == "__main__":

    print("=" * 52)
    print("VED  --  SENSORS")
    print("=" * 52)

    print(f"\nLink: {sensorStatus()}\n")

    if not esp32.connected():

        print("No ESP32 attached.\n")

        print(f"  getSensors()   -> {getSensors()}")
        print(f"  getDistances() -> {getDistances()}")
        print(f"  sensorsFresh() -> {sensorsFresh()}")

        print(
            "\nNote getDistances() returns all None rather"
            "\nthan zeros. Zero would read as 'obstacle at"
            "\n0cm'; None reads as 'unknown', which is what"
            "\nthe navigator already handles."
        )

    else:

        print("Polling for 5s...\n")

        end = time.time() + 5

        while time.time() < end:

            distances = getDistances()

            print(
                f"  front {str(distances['front']):>6}  "
                f"left {str(distances['left']):>6}  "
                f"right {str(distances['right']):>6}   "
                f"fresh={sensorsFresh()}"
            )

            time.sleep(0.5)
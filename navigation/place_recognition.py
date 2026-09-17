"""
=========================================================
navigation/place_recognition.py

Recognising rooms without markers.

Author: Pranjal

THE PROBLEM WITH HOMES
----------------------
Nobody will let you tape ArUco markers around their
house, and homes have no room number plates. But a home
is full of landmarks already -- they are just not
designed to be landmarks.

THREE SIGNALS, FUSED
--------------------

1. OBJECTS  (what is in this room)
   A fridge, microwave and sink means kitchen. A bed
   means bedroom. YOLO already gives you this, and it is
   robust to lighting and viewpoint.

   Strong at ROOM TYPE. Useless at telling one bedroom
   from another -- they all contain a bed.

2. APPEARANCE  (what this room looks like)
   ORB features of the view. Different furniture,
   colours, layout. This is what separates Pranjal's
   room from the in-laws' room.

   Fragile: breaks with lighting changes, rearranged
   furniture, or someone standing in the way.

3. WIFI  (where this room is)
   Signal strength from each access point differs by
   room, because walls attenuate. Genuinely underrated
   indoors -- works in total darkness, costs no compute,
   and does not care what the room looks like.

   Coarse, and drifts if the router moves.

NONE OF THESE IS RELIABLE ALONE. Fused with confidence
weighting, they are decent -- and crucially, when they
disagree the confidence drops, so Ved can say "I think
this is the kitchen" instead of asserting nonsense.

TEACHING, NOT CONFIGURING
-------------------------
The interaction is: walk Ved into a room and say "this
is the kitchen". It captures several samples and stores
them. That is the only setup a home user will tolerate.
=========================================================
"""

import json
import platform
import subprocess
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PLACES_FILE = DATA_DIR / "places.json"
DESCRIPTOR_DIR = DATA_DIR / "place_features"


####################################################
# Objects that strongly imply a room type
#
# Weighted because a fridge is far more diagnostic of a
# kitchen than a chair is of anything.
####################################################

ROOM_HINTS = {
    "kitchen": {
        "refrigerator": 3.0, "microwave": 3.0, "oven": 2.5,
        "sink": 2.0, "bottle": 0.5, "cup": 0.5, "bowl": 1.0,
    },
    "bedroom": {
        "bed": 4.0, "clock": 0.5, "book": 0.5,
    },
    "living_room": {
        "couch": 3.0, "tv": 2.5, "remote": 1.5,
        "potted plant": 1.0, "chair": 0.5,
    },
    "dining": {
        "dining table": 3.0, "chair": 1.0, "bowl": 0.5,
        "wine glass": 1.0,
    },
    "bathroom": {
        "toilet": 4.0, "sink": 1.5, "hair drier": 2.0,
        "toothbrush": 2.5,
    },
    "office": {
        "laptop": 2.5, "keyboard": 2.0, "mouse": 2.0,
        "book": 1.0, "chair": 0.5, "tv": 0.5,
    },
}


# Fusion weights. Appearance carries the most because it
# is the only signal that distinguishes two rooms of the
# same type -- which is the actual hard case.
WEIGHT_OBJECTS = 0.30
WEIGHT_APPEARANCE = 0.45
WEIGHT_WIFI = 0.25

# Below this, Ved should say "I think" rather than assert.
CONFIDENT = 0.55
UNCERTAIN = 0.30

SAMPLES_PER_PLACE = 6
MAX_DESCRIPTORS = 400


####################################################
# WiFi fingerprinting
####################################################

def scan_wifi():
    """
    {bssid: signal_dbm} for visible access points.

    Returns {} when unavailable -- the fusion handles a
    missing signal by reweighting, so this degrading is
    fine rather than fatal.
    """

    system = platform.system()

    try:
        if system == "Darwin":
            return _scan_wifi_macos()

        if system == "Linux":
            return _scan_wifi_linux()

    except Exception:
        pass

    return {}


def _scan_wifi_macos():

    # airport was removed in recent macOS. Try it, but
    # expect nothing on a current machine.
    path = (
        "/System/Library/PrivateFrameworks/Apple80211.framework"
        "/Versions/Current/Resources/airport"
    )

    output = subprocess.run(
        [path, "-s"],
        capture_output=True,
        text=True,
        timeout=8
    ).stdout

    networks = {}

    for line in output.splitlines()[1:]:

        parts = line.split()

        if len(parts) < 3:
            continue

        bssid = parts[1]
        try:
            networks[bssid] = int(parts[2])
        except ValueError:
            continue

    return networks


def _scan_wifi_linux():
    """
    nmcli on Pi OS Bookworm. Needs no root.
    """

    output = subprocess.run(
        [
            "nmcli", "-t", "-f", "BSSID,SIGNAL",
            "device", "wifi", "list", "--rescan", "no"
        ],
        capture_output=True,
        text=True,
        timeout=8
    ).stdout

    networks = {}

    for line in output.splitlines():

        # BSSID contains escaped colons: AA\:BB\:CC...
        parts = line.replace("\\:", ":").rsplit(":", 1)

        if len(parts) != 2:
            continue

        try:
            # nmcli SIGNAL is 0-100; convert to rough dBm
            networks[parts[0]] = int(parts[1]) - 100
        except ValueError:
            continue

    return networks


def wifi_similarity(a, b):
    """
    How alike are two WiFi fingerprints? 0..1

    Compares only access points seen in BOTH, then
    penalises by how little they overlap. Two scans
    sharing one weak router should not score highly just
    because that one matches.
    """

    if not a or not b:
        return None

    shared = set(a) & set(b)

    if not shared:
        return 0.0

    differences = [abs(a[bssid] - b[bssid]) for bssid in shared]

    mean_difference = sum(differences) / len(differences)

    # 0 dBm apart -> 1.0, 25 dBm apart -> 0.0
    closeness = max(0.0, 1.0 - mean_difference / 25.0)

    overlap = len(shared) / max(len(a), len(b))

    return closeness * (0.4 + 0.6 * overlap)


####################################################
# Place
####################################################

@dataclass
class Place:

    name: str
    room_type: str = ""

    # Averaged object counts across samples.
    objects: dict = field(default_factory=dict)

    # Averaged WiFi fingerprint.
    wifi: dict = field(default_factory=dict)

    samples: int = 0
    taught_at: float = field(default_factory=time.time)

    # Who is usually found here. A weak signal on its own,
    # but it breaks ties between rooms of the same type --
    # the in-laws' room is where the in-laws are.
    people: dict = field(default_factory=dict)

    def descriptor_path(self):

        return DESCRIPTOR_DIR / f"{self.name}.npy"


class PlaceRecognition:

    def __init__(self):

        self.places = {}

        self._descriptors = {}

        self._matcher = None

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        DESCRIPTOR_DIR.mkdir(parents=True, exist_ok=True)

    ####################################################
    # Signals
    ####################################################

    @staticmethod
    def object_signature(detections):
        """
        {label: count} from YOLO detections.
        """

        return dict(Counter(d["label"] for d in detections or []))

    ####################################################

    @staticmethod
    def guess_room_type(objects):
        """
        Best room type from what is visible, plus a score.
        """

        if not objects:
            return "", 0.0

        scores = {}

        for room_type, hints in ROOM_HINTS.items():

            score = sum(
                weight * min(objects.get(label, 0), 2)
                for label, weight in hints.items()
            )

            scores[room_type] = score

        best = max(scores.items(), key=lambda kv: kv[1])

        if best[1] <= 0:
            return "", 0.0

        total = sum(scores.values()) or 1.0

        return best[0], round(best[1] / total, 2)

    ####################################################

    @staticmethod
    def object_similarity(a, b):
        """
        Cosine similarity over object counts.
        """

        if not a or not b:
            return None

        labels = set(a) | set(b)

        vector_a = np.array([a.get(l, 0) for l in labels], dtype=float)
        vector_b = np.array([b.get(l, 0) for l in labels], dtype=float)

        norm = np.linalg.norm(vector_a) * np.linalg.norm(vector_b)

        if norm == 0:
            return 0.0

        return float(np.dot(vector_a, vector_b) / norm)

    ####################################################

    def extract_features(self, frame):
        """
        ORB descriptors for the current view.
        """

        import cv2

        if frame is None:
            return None

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Equalise so a bright and a dim view of the same
        # room produce comparable features. Helps; does
        # not fully solve it.
        gray = cv2.equalizeHist(gray)

        orb = cv2.ORB_create(nfeatures=MAX_DESCRIPTORS)

        _, descriptors = orb.detectAndCompute(gray, None)

        return descriptors

    ####################################################

    def appearance_similarity(self, descriptors, stored):
        """
        Fraction of features that match well. 0..1
        """

        import cv2

        if descriptors is None or stored is None:
            return None

        if len(descriptors) < 10 or len(stored) < 10:
            return None

        if self._matcher is None:
            self._matcher = cv2.BFMatcher(cv2.NORM_HAMMING)

        try:
            matches = self._matcher.knnMatch(descriptors, stored, k=2)

        except cv2.error:
            return None

        good = 0

        for match in matches:

            if len(match) < 2:
                continue

            # Lowe's ratio test: a match is only
            # trustworthy if it is clearly better than the
            # second-best candidate.
            if match[0].distance < 0.75 * match[1].distance:
                good += 1

        return min(1.0, good / max(20.0, len(descriptors) * 0.25))

    ####################################################
    # Teaching
    ####################################################

    def teach(self, name, frames, detections_per_frame=None, room_type=""):
        """
        Learn a place from several views.

        frames: list of BGR frames, ideally from different
                angles in the same room. One view teaches
                Ved one doorway, not one room.
        """

        if not frames:
            return None, "no frames"

        object_totals = Counter()

        all_descriptors = []

        for index, frame in enumerate(frames):

            descriptors = self.extract_features(frame)

            if descriptors is not None:
                all_descriptors.append(descriptors)

            if detections_per_frame and index < len(detections_per_frame):
                for label, count in self.object_signature(
                    detections_per_frame[index]
                ).items():
                    object_totals[label] += count

        if not all_descriptors:
            return None, "no visual features -- too dark or too plain"

        descriptors = np.vstack(all_descriptors)

        # Cap stored descriptors: matching cost scales
        # with this and there are diminishing returns.
        if len(descriptors) > MAX_DESCRIPTORS * 3:

            indices = np.random.choice(
                len(descriptors),
                MAX_DESCRIPTORS * 3,
                replace=False
            )

            descriptors = descriptors[indices]

        objects = {
            label: round(count / len(frames), 2)
            for label, count in object_totals.items()
        }

        if not room_type:
            room_type, _ = self.guess_room_type(objects)

        place = Place(
            name=name,
            room_type=room_type,
            objects=objects,
            wifi=scan_wifi(),
            samples=len(frames),
        )

        self.places[name] = place
        self._descriptors[name] = descriptors

        np.save(place.descriptor_path(), descriptors)

        self.save()

        return place, None

    ####################################################

    def note_person(self, place_name, person):
        """
        Remember who tends to be found here.
        """

        place = self.places.get(place_name)

        if place is None or person == "Unknown":
            return

        place.people[person] = place.people.get(person, 0) + 1

        self.save()

    ####################################################
    # Recognition
    ####################################################

    def identify(self, frame, detections=None, person=None):
        """
        Where are we?

        Returns {name, confidence, room_type, scores, sure}
        or None if nothing is known yet.
        """

        if not self.places:
            return None

        descriptors = self.extract_features(frame)

        objects = self.object_signature(detections)

        wifi = scan_wifi()

        results = []

        for name, place in self.places.items():

            stored = self._descriptors.get(name)

            if stored is None and place.descriptor_path().exists():
                stored = np.load(place.descriptor_path())
                self._descriptors[name] = stored

            ############################################
            # Individual signals -- None means "no
            # opinion", which is different from zero
            ############################################

            appearance = self.appearance_similarity(descriptors, stored)

            object_score = self.object_similarity(objects, place.objects)

            wifi_score = wifi_similarity(wifi, place.wifi)

            ############################################
            # Fuse, reweighting over whatever is present
            ############################################

            parts = []

            if appearance is not None:
                parts.append((appearance, WEIGHT_APPEARANCE))

            if object_score is not None:
                parts.append((object_score, WEIGHT_OBJECTS))

            if wifi_score is not None:
                parts.append((wifi_score, WEIGHT_WIFI))

            if not parts:
                continue

            total_weight = sum(w for _, w in parts)

            confidence = sum(s * w for s, w in parts) / total_weight

            ############################################
            # Who is here nudges the tie
            ############################################

            if person and person in place.people:

                visits = place.people[person]
                total = sum(place.people.values()) or 1

                confidence += 0.08 * (visits / total)

            results.append(
                {
                    "name": name,
                    "confidence": round(min(1.0, confidence), 3),
                    "room_type": place.room_type,
                    "scores": {
                        "appearance": (
                            round(appearance, 2)
                            if appearance is not None else None
                        ),
                        "objects": (
                            round(object_score, 2)
                            if object_score is not None else None
                        ),
                        "wifi": (
                            round(wifi_score, 2)
                            if wifi_score is not None else None
                        ),
                    },
                }
            )

        if not results:
            return None

        results.sort(key=lambda r: -r["confidence"])

        best = results[0]

        best["sure"] = best["confidence"] >= CONFIDENT

        ################################################
        # Ambiguity check
        #
        # A high score means little if the runner-up is
        # nearly as high -- that is exactly the two
        # identical bedrooms case, and asserting either
        # would be wrong half the time.
        ################################################

        if len(results) > 1:

            margin = best["confidence"] - results[1]["confidence"]

            best["margin"] = round(margin, 3)

            if margin < 0.10:
                best["sure"] = False
                best["ambiguous_with"] = results[1]["name"]

        best["alternatives"] = results[1:3]

        return best

    ####################################################

    def describe(self, result):
        """
        How Ved should talk about where it is.
        """

        if result is None:
            return "I don't recognise this place."

        name = result["name"].replace("_", " ")

        if result.get("ambiguous_with"):
            other = result["ambiguous_with"].replace("_", " ")
            return f"This looks like {name}, but it might be {other}."

        if result["confidence"] >= CONFIDENT:
            return f"This is {name}."

        if result["confidence"] >= UNCERTAIN:
            return f"I think this is {name}."

        return "I'm not sure where I am."

    ####################################################
    # Persistence
    ####################################################

    def save(self):

        data = {
            "saved_at": time.time(),
            "places": [
                {
                    "name": p.name,
                    "room_type": p.room_type,
                    "objects": p.objects,
                    "wifi": p.wifi,
                    "samples": p.samples,
                    "taught_at": p.taught_at,
                    "people": p.people,
                }
                for p in self.places.values()
            ],
        }

        tmp = PLACES_FILE.with_suffix(".tmp")

        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)

        tmp.replace(PLACES_FILE)

    ####################################################

    def load(self):

        if not PLACES_FILE.exists():
            return 0

        try:
            with open(PLACES_FILE) as f:
                data = json.load(f)

        except Exception as exc:
            print(f"[PLACES] Could not load: {exc}")
            return 0

        for entry in data.get("places", []):

            self.places[entry["name"]] = Place(
                name=entry["name"],
                room_type=entry.get("room_type", ""),
                objects=entry.get("objects", {}),
                wifi=entry.get("wifi", {}),
                samples=entry.get("samples", 0),
                taught_at=entry.get("taught_at", 0),
                people=entry.get("people", {}),
            )

        return len(self.places)

    ####################################################

    def forget(self, name):

        if name not in self.places:
            return False

        path = self.places[name].descriptor_path()

        if path.exists():
            path.unlink()

        del self.places[name]
        self._descriptors.pop(name, None)

        self.save()

        return True


####################################################
# Singleton
####################################################

place_recognition = PlaceRecognition()


####################################################

if __name__ == "__main__":

    print("=" * 58)
    print("VED PLACE RECOGNITION")
    print("=" * 58)

    recogniser = PlaceRecognition()

    ################################################
    # Room type from objects alone
    ################################################

    print("\n--- Room type from what YOLO sees ---\n")

    scenes = {
        "a kitchen": [
            {"label": "refrigerator"}, {"label": "microwave"},
            {"label": "sink"}, {"label": "bottle"},
        ],
        "a bedroom": [
            {"label": "bed"}, {"label": "clock"}, {"label": "book"},
        ],
        "a living room": [
            {"label": "couch"}, {"label": "tv"},
            {"label": "potted plant"},
        ],
        "an office": [
            {"label": "laptop"}, {"label": "keyboard"},
            {"label": "mouse"}, {"label": "chair"},
        ],
    }

    for label, detections in scenes.items():

        objects = recogniser.object_signature(detections)

        room_type, score = recogniser.guess_room_type(objects)

        print(f"  {label:<16} -> {room_type:<12} ({score})")

    ################################################
    # The hard case
    ################################################

    print("\n--- Why two bedrooms need more than objects ---\n")

    pranjal = recogniser.object_signature(
        [{"label": "bed"}, {"label": "laptop"}, {"label": "book"}]
    )

    inlaws = recogniser.object_signature(
        [{"label": "bed"}, {"label": "clock"}, {"label": "book"}]
    )

    print(
        f"  object similarity between the two bedrooms: "
        f"{recogniser.object_similarity(pranjal, inlaws):.2f}"
    )

    print(
        "\n  Nearly identical. Appearance and WiFi are what"
        "\n  actually separate them -- hence the fusion."
    )

    ################################################
    # WiFi
    ################################################

    print("\n--- WiFi fingerprint comparison ---\n")

    kitchen = {"aa:bb:01": -45, "aa:bb:02": -70, "aa:bb:03": -80}
    same_kitchen = {"aa:bb:01": -48, "aa:bb:02": -68, "aa:bb:03": -83}
    far_bedroom = {"aa:bb:01": -75, "aa:bb:02": -50, "aa:bb:03": -60}

    print(
        f"  kitchen vs kitchen again : "
        f"{wifi_similarity(kitchen, same_kitchen):.2f}"
    )
    print(
        f"  kitchen vs far bedroom   : "
        f"{wifi_similarity(kitchen, far_bedroom):.2f}"
    )

    found = scan_wifi()

    print(
        f"\n  This machine sees {len(found)} access point(s)"
        + ("" if found else "  (scanning unavailable here)")
    )

    print(
        "\n  Note: works in complete darkness, which is"
        "\n  exactly where the camera signals fail."
    )
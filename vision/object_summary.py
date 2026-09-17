"""
object_summary.py

Creates a human-readable summary
of detected objects.
"""

from collections import Counter


def summarize_objects(detections):

    if not detections:

        return "I don't see any objects."

    counts = Counter()

    for obj in detections:

        counts[obj["label"]] += 1

    parts = []

    for label, count in sorted(counts.items()):

        if count == 1:

            parts.append(f"one {label}")

        else:

            parts.append(f"{count} {label}s")

    return "I can see " + ", ".join(parts) + "."
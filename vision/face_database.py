"""
=========================================================
face_database.py

Stores face templates and per-person profile data.

Author: Pranjal

WHAT LIVES WHERE
----------------
This file      -> WHO someone is, and stable facts about
                  them: face templates, preferred
                  language, dietary notes, room number.
                  Changes rarely. Edited deliberately.

social_memory  -> WHAT HAS HAPPENED: visit count, last
                  seen, greeting cooldowns. Changes every
                  time Ved sees them.

Keeping visit history out of here is deliberate. Two
files both claiming to know the visit count will drift
apart, and the stale one always wins an argument at the
worst moment.

MULTI-TEMPLATE STORAGE
----------------------
Each person holds SEVERAL templates -- bright, dim,
with glasses -- and matching takes the BEST score across
them rather than one blurred average.

Storage layout:
    known_faces/<name>/templates.npy   (N x D float32)
    known_faces/<name>/meta.json

Legacy embedding.npy folders still load.
=========================================================
"""

import json
import time

import numpy as np

from vision.config import FACE_DB_DIR, FACE_MODEL


MAX_TEMPLATES = 12

DEFAULT_LANGUAGE = "English"

SUPPORTED_LANGUAGES = {
    "English", "Hindi", "Marathi",
    "Gujarati", "Rajasthani",
}


####################################################
# Vector helpers
####################################################

def normalise(embedding):
    """L2-normalise so cosine similarity == dot product."""

    embedding = np.asarray(embedding, dtype=np.float32)

    if embedding.ndim == 1:

        norm = np.linalg.norm(embedding)

        return embedding if norm == 0 else embedding / norm

    norms = np.linalg.norm(embedding, axis=1, keepdims=True)

    norms[norms == 0] = 1.0

    return embedding / norms


def average_embeddings(embeddings):
    """
    Mean of several samples, renormalised.

    Valid WITHIN one condition -- five frames seconds
    apart in the same light are one observation, so
    averaging removes noise. Averaging ACROSS conditions
    is what multi-template storage exists to avoid.
    """

    if embeddings is None or not len(embeddings):
        return None

    stacked = normalise(
        np.stack([np.asarray(e) for e in embeddings])
    )

    return normalise(stacked.mean(axis=0))


####################################################
# Pruning
####################################################

def prune_templates(templates, limit=MAX_TEMPLATES):
    """
    Keep the most DIVERSE templates, not the newest.

    Drops whichever template is most similar to another,
    since it carries the least new information. Dropping
    oldest-first would slowly discard your daylight
    enrollment as you kept testing at night.
    """

    templates = normalise(np.asarray(templates, dtype=np.float32))

    if len(templates) <= limit:
        return templates

    keep = list(range(len(templates)))

    while len(keep) > limit:

        subset = templates[keep]

        similarity = subset @ subset.T

        np.fill_diagonal(similarity, -1.0)

        redundant = int(np.argmax(similarity.max(axis=1)))

        keep.pop(redundant)

    return templates[keep]


####################################################
# Paths / meta
####################################################

def _folder(name):

    return FACE_DB_DIR / name


def _read_meta(name):

    path = _folder(name) / "meta.json"

    if not path.exists():
        return {}

    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def _write_meta(name, meta):

    folder = _folder(name)

    folder.mkdir(parents=True, exist_ok=True)

    tmp = folder / "meta.tmp"

    with open(tmp, "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    # Atomic: a power cut mid-write leaves the old file
    # intact rather than a truncated one.
    tmp.replace(folder / "meta.json")


def _blank_meta(name):

    return {
        "name": name,
        "model": FACE_MODEL,
        "templates": 0,
        "enrolled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sessions": [],
        "profile": {
            "preferred_language": DEFAULT_LANGUAGE,
            "role": "",
            "room": "",
            "notes": "",
        },
    }


####################################################
# Load
####################################################

def load_templates(name):
    """
    All templates for one person as (N, D), or None.
    """

    folder = _folder(name)

    new_path = folder / "templates.npy"
    old_path = folder / "embedding.npy"

    try:
        if new_path.exists():
            data = np.load(new_path)

        elif old_path.exists():
            data = np.load(old_path)

        else:
            return None

    except Exception as exc:
        print(f"[FACE DB] Could not load {name}: {exc}")
        return None

    if data.ndim == 1:
        data = data.reshape(1, -1)

    return normalise(data)


def load_faces():
    """
    Returns {name: (N, D) normalised templates}.

    Skips anyone enrolled with a different model, loudly.
    """

    faces = {}

    if not FACE_DB_DIR.exists():
        return faces

    mismatched = []

    for folder in sorted(FACE_DB_DIR.iterdir()):

        if not folder.is_dir():
            continue

        templates = load_templates(folder.name)

        if templates is None:
            continue

        stored_model = _read_meta(folder.name).get("model")

        # Embeddings are NOT portable across models. A
        # buffalo_l template scored against a buffalo_sc
        # query returns noise -- no error, just a
        # meaningless number near zero.
        if stored_model and stored_model != FACE_MODEL:
            mismatched.append(f"{folder.name} ({stored_model})")
            continue

        faces[folder.name] = templates

    if mismatched:
        print(
            "[FACE DB] IGNORED -- enrolled with a different "
            f"model, re-enroll these: {', '.join(mismatched)}"
        )

    return faces


####################################################
# Save templates
####################################################

def add_templates(name, embeddings, condition="default"):
    """
    Add templates for a person, keeping existing ones.

    condition: free-text label ("bright", "dim") stored in
    meta so you can see what coverage someone has.

    Returns the total template count after adding.
    """

    embeddings = np.asarray(embeddings, dtype=np.float32)

    if embeddings.ndim == 1:
        embeddings = embeddings.reshape(1, -1)

    embeddings = normalise(embeddings)

    existing = load_templates(name)

    if (
        existing is not None
        and existing.shape[1] == embeddings.shape[1]
    ):
        combined = np.vstack([existing, embeddings])
    else:
        combined = embeddings

    combined = prune_templates(combined)

    folder = _folder(name)

    folder.mkdir(parents=True, exist_ok=True)

    np.save(folder / "templates.npy", combined.astype(np.float32))

    # Drop the legacy file so it cannot shadow the new one.
    legacy = folder / "embedding.npy"

    if legacy.exists():
        legacy.unlink()

    ################################################
    # Meta -- preserve the profile across re-enrollment
    ################################################

    meta = _read_meta(name) or _blank_meta(name)

    meta.setdefault("name", name)
    meta.setdefault("enrolled_at", time.strftime("%Y-%m-%d %H:%M:%S"))
    meta.setdefault("sessions", [])
    meta.setdefault("profile", _blank_meta(name)["profile"])

    meta["model"] = FACE_MODEL
    meta["templates"] = int(len(combined))

    meta["sessions"].append(
        {
            "condition": condition,
            "added": time.strftime("%Y-%m-%d %H:%M:%S"),
            "count": int(len(embeddings)),
        }
    )

    _write_meta(name, meta)

    return int(len(combined))


def save_face(name, embedding, samples=1, condition="default"):
    """
    Replace all templates for this person.

    Kept for compatibility. Prefer add_templates(), which
    accumulates coverage instead of discarding it.
    The profile is preserved either way.
    """

    profile = get_profile(name)

    folder = _folder(name)

    if folder.exists():
        for item in folder.iterdir():
            item.unlink()

    total = add_templates(name, embedding, condition=condition)

    if profile:
        set_profile(name, **profile)

    return total


####################################################
# Profile
####################################################

def get_profile(name):
    """
    Stable facts about a person. {} if unknown.
    """

    meta = _read_meta(name)

    if not meta:
        return {}

    profile = dict(_blank_meta(name)["profile"])

    profile.update(meta.get("profile", {}))

    return profile


def set_profile(name, **fields):
    """
    Update profile fields. Only the keys you pass change.

        set_profile("Pranjal", preferred_language="Hindi")
        set_profile("Rahul", role="staff", room="204")
    """

    folder = _folder(name)

    if not folder.exists():
        print(f"[FACE DB] '{name}' is not enrolled.")
        return None

    meta = _read_meta(name) or _blank_meta(name)

    profile = dict(_blank_meta(name)["profile"])
    profile.update(meta.get("profile", {}))

    language = fields.get("preferred_language")

    if language and language not in SUPPORTED_LANGUAGES:
        print(
            f"[FACE DB] Warning: '{language}' is not in "
            f"SUPPORTED_LANGUAGES. Storing it anyway."
        )

    profile.update({k: v for k, v in fields.items() if v is not None})

    meta["profile"] = profile

    _write_meta(name, meta)

    return profile


def get_language(name):
    """
    Which language should Ved greet this person in?
    """

    return get_profile(name).get(
        "preferred_language", DEFAULT_LANGUAGE
    )


####################################################
# Auto-learning
#
# Registration happens ONCE. But Ved sees people many
# times afterwards, in conditions the enrollment never
# covered. When it recognises someone CONFIDENTLY in a
# condition it has no template for, it quietly keeps
# that observation.
#
# No prompt, no interaction. The database gets better
# every time someone walks past.
####################################################

# Only learn from matches well clear of the lock
# threshold. Learning from a marginal match is how a
# database poisons itself: one wrong template makes the
# next wrong match easier, and it compounds.
AUTO_LEARN_MIN_SCORE = 0.68

# Never learn twice for the same condition -- otherwise
# the most common lighting crowds out everything else.
# One template per condition bucket is the whole point.
AUTO_LEARN_ONE_PER_CONDITION = True


def learned_conditions(name):
    """Condition labels this person already has."""

    meta = _read_meta(name)

    return {
        session.get("condition")
        for session in meta.get("sessions", [])
    }


def auto_learn(name, embedding, condition, score):
    """
    Maybe add a template, silently.

    Returns the condition learned, or None if declined.
    """

    if score < AUTO_LEARN_MIN_SCORE:
        return None

    if not condition or condition == "default":
        return None

    if (
        AUTO_LEARN_ONE_PER_CONDITION
        and condition in learned_conditions(name)
    ):
        return None

    if load_templates(name) is None:
        return None

    add_templates(name, embedding, condition=f"auto:{condition}")

    print(
        f"[FACE DB] Learned '{name}' in {condition} "
        f"conditions (score {score:.2f})"
    )

    return condition


####################################################
# Manage
####################################################

def list_faces():

    return sorted(load_faces().keys())


def delete_face(name):

    folder = _folder(name)

    if not folder.exists():
        return False

    for item in folder.iterdir():
        item.unlink()

    folder.rmdir()

    return True


def face_info(name):

    meta = _read_meta(name)

    if not meta:
        return None

    templates = load_templates(name)

    if templates is not None:
        meta["templates"] = int(len(templates))

    meta["profile"] = get_profile(name)

    return meta


####################################################

if __name__ == "__main__":

    known = list_faces()

    if not known:
        print(f"No faces enrolled. Database: {FACE_DB_DIR}")
        print(f"Current model: {FACE_MODEL}")

    else:
        print(f"{len(known)} face(s) in {FACE_DB_DIR}")
        print(f"Model: {FACE_MODEL}\n")

        for person in known:

            info = face_info(person) or {}
            profile = info.get("profile", {})

            print(f"  {person}")
            print(f"    templates : {info.get('templates', '?')}")
            print(
                f"    language  : "
                f"{profile.get('preferred_language', '?')}"
            )

            if profile.get("role"):
                print(f"    role      : {profile['role']}")

            if profile.get("room"):
                print(f"    room      : {profile['room']}")

            if profile.get("notes"):
                print(f"    notes     : {profile['notes']}")

            for session in info.get("sessions", []):
                print(
                    f"      + {session.get('count')} "
                    f"[{session.get('condition')}] "
                    f"{session.get('added')}"
                )

            print()
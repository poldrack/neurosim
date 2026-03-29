import json
import random
from pathlib import Path


def load_disorders(filepath: Path) -> list[dict]:
    """Load disorder taxonomy JSON and return a flat list of disorders.

    Each disorder dict gets a 'category' field added from its parent category.
    """
    with open(filepath) as f:
        data = json.load(f)

    disorders = []
    for category in data["categories"]:
        for disorder in category["disorders"]:
            entry = dict(disorder)
            entry["category"] = category["category"]
            disorders.append(entry)
    return disorders


def get_random_disorder(disorders: list[dict]) -> dict:
    """Return a randomly selected disorder from the list."""
    return random.choice(disorders)

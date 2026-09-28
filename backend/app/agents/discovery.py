"""Data Discovery agent: chooses datasets per intent. No fetching itself."""

_INTENTS = ("safety", "pfz", "zone", "route")


def choose(intent: str) -> dict:
    table = {
        "safety": ["forecast", "alerts", "tides"],
        "pfz": ["pfz", "sst", "chlorophyll"],
        "zone": ["eez", "mpa"],
        "route": ["mpa", "forecast", "alerts"],
    }
    return {"intent": intent, "datasets": table.get(intent, ["forecast"])}

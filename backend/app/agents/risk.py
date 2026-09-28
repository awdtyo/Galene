"""Risk agent: DETERMINISTIC safe/caution/unsafe verdict. Rules only, no ML/LLM.

Provisional thresholds (documented, pending domain review):
- wind > 61 km/h -> unsafe; > 40 km/h -> caution
- wave > 4.0 m -> unsafe; > 2.5 m -> caution
- any IMD warning not equal to "No warning" -> at least caution
"""

from backend.app.api.schemas import now_iso

UNSAFE_WIND, CAUTION_WIND = 61.0, 40.0
UNSAFE_WAVE, CAUTION_WAVE = 4.0, 2.5


def verdict(summary: dict, trace: list) -> dict:
    reasons, level = [], 0  # 0 safe, 1 caution, 2 unsafe
    w = summary.get("max_wind_kmh")
    if w is not None:
        if w > UNSAFE_WIND:
            level, reasons = 2, reasons + [f"Wind {w:.0f} km/h exceeds unsafe limit {UNSAFE_WIND:.0f}."]
        elif w > CAUTION_WIND:
            level = max(level, 1)
            reasons.append(f"Wind {w:.0f} km/h above caution limit {CAUTION_WIND:.0f}.")
        else:
            reasons.append(f"Wind {w:.0f} km/h within limits.")
    m = summary.get("max_wave_m")
    if m is not None:
        if m > UNSAFE_WAVE:
            level, reasons = 2, reasons + [f"Waves {m:.1f} m exceed unsafe limit {UNSAFE_WAVE:.1f} m."]
        elif m > CAUTION_WAVE:
            level = max(level, 1)
            reasons.append(f"Waves {m:.1f} m above caution limit {CAUTION_WAVE:.1f} m.")
        else:
            reasons.append(f"Waves {m:.1f} m within limits.")
    for wr in summary.get("warnings", []):
        if str(wr.get("warning", "")).lower() != "no warning":
            level = max(level, 1)
            reasons.append(f"IMD warning: {wr.get('warning')}.")
    trace.append({"agent": "risk", "tool": None, "timestamp": now_iso()})
    return {"verdict": ["safe", "caution", "unsafe"][level], "reasons": reasons}

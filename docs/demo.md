# ORCA Demo Script (Phase 6)

## 1. Start backend (needs `.env` with Groq key for live LLM, else mock)
```bash
uvicorn backend.app.main:app --port 8000
```

## 2. Serve UI
```bash
cd frontend && python3 -m http.server 8080
# open http://localhost:8080 — chat (right), map (left), trace viewer (bottom)
```

## 3. Seed queries (map click sets lat/lon; default Kochi 15.0, 74.0)
1. `Is it safe tomorrow morning?` → expect verdict + Geofence line + trace
   planner → weather ×3 → risk → geo → viz, citations present.
2. `Regions with high chlorophyll and favourable SST?` → PFZ facts + citations.
3. `Which zones to avoid?` (click Sundarbans ~21.9, 88.9) → MPA warning.
4. `Safest route?` with dest → distance + MPA detour + departure verdict.

## 4. Proactive alerts CLI
```bash
python3 scripts/check_alerts.py --mock   # offline
python3 scripts/check_alerts.py          # live (uses .env provider)
```

## 5. Map tour
Toggle EEZ / MPAs / PFZ layers; PFZ markers show depth + direction popups.
Evidence viewer shows reasons, citations, agent/tool/timestamp trace.

## 6. Tests
```bash
python3 -m pytest -q   # 30+ tests incl. English-only eval set
```

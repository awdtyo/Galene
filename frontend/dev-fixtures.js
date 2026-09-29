/* ==========================================================================
   Galene — development fixtures (FRONTEND ONLY, TEST ONLY)
   --------------------------------------------------------------------------
   Loaded by index.html but completely inert unless the page is opened with a
   flag such as  /?mock=degraded  or  /?mock=error  or  /?mock=empty-trace.

   `safety` and `pfz` are VERBATIM captures of real POST /ask responses taken
   from the running backend. `degraded` is the verbatim `pfz` capture with the
   two fields the backend emits on its replan path applied — the
   `planner / replan:pfz` trace step and `degraded: true` (see
   backend/app/agents/planner.py:43-46,85,143). It is a local copy used to
   exercise the degraded UI state, not a live response.

   `error` is a marker only; it makes the UI render its network-error state.

   Nothing here reaches the backend, and no marine value is invented: every
   number below was produced by the backend itself.
   ========================================================================== */

window.GALENE_DEV_FIXTURES = {
  safety: {
    answer: "[SAFE] Window 2026-09-30 04:00-11:00: max wind 12.7 km/h, max wave 0.84 m. Reasons: Wind 13 km/h within limits.; Waves 0.8 m within limits. Geofence: inside Indian EEZ, clear of protected areas.. Sources: forecast_provenance, incois_advisories.",
    verdict: "safe",
    reasons: ["Wind 13 km/h within limits.", "Waves 0.8 m within limits."],
    trace: [
      { agent: "planner", tool: "classify:safety", timestamp: "2026-09-29T14:31:29Z" },
      { agent: "planner", tool: "discovery:forecast,alerts,tides", timestamp: "2026-09-29T14:31:29Z" },
      { agent: "weather", tool: "get_forecast", timestamp: "2026-09-29T14:31:29Z" },
      { agent: "weather", tool: "get_alerts", timestamp: "2026-09-29T14:31:29Z" },
      { agent: "weather", tool: "get_tides", timestamp: "2026-09-29T14:31:29Z" },
      { agent: "risk", tool: null, timestamp: "2026-09-29T14:31:29Z" },
      { agent: "geo", tool: "check_geofence", timestamp: "2026-09-29T14:31:29Z" },
      { agent: "viz", tool: "llm:mock", timestamp: "2026-09-29T14:31:29Z" }
    ],
    session_id: "probe-1",
    citations: ["forecast_provenance", "incois_advisories"],
    degraded: false
  },

  pfz: {
    answer: "PFZ: 1 zone(s); SST 28.9 C, chlorophyll 0.42 mg/m3. Conditions look favourable. PFZ correlation baseline: warm SST + elevated chlorophyll suggest productivity.. Sources: incois_advisories, safety_thresholds.",
    verdict: "info",
    reasons: [],
    trace: [
      { agent: "planner", tool: "classify:pfz", timestamp: "2026-09-29T14:31:29Z" },
      { agent: "planner", tool: "discovery:pfz,sst,chlorophyll", timestamp: "2026-09-29T14:31:29Z" },
      { agent: "ocean", tool: "get_sst", timestamp: "2026-09-29T14:31:29Z" },
      { agent: "ocean", tool: "get_chlorophyll", timestamp: "2026-09-29T14:31:29Z" },
      { agent: "ocean", tool: "get_pfz", timestamp: "2026-09-29T14:31:29Z" },
      { agent: "viz", tool: "llm:mock", timestamp: "2026-09-29T14:31:29Z" }
    ],
    session_id: "probe-1",
    citations: ["incois_advisories", "safety_thresholds"],
    degraded: false
  },

  /* Real `pfz` capture + the replan step and degraded flag the backend emits
     when a potential-fishing-zone query returns zero zones. */
  degraded: {
    answer: "PFZ: 0 zone(s); SST 28.9 C, chlorophyll 0.42 mg/m3. Conditions look favourable. PFZ correlation baseline: warm SST + elevated chlorophyll suggest productivity.. Sources: incois_advisories, safety_thresholds.",
    verdict: "info",
    reasons: [],
    trace: [
      { agent: "planner", tool: "classify:pfz", timestamp: "2026-09-29T14:31:29Z" },
      { agent: "planner", tool: "discovery:pfz,sst,chlorophyll", timestamp: "2026-09-29T14:31:29Z" },
      { agent: "ocean", tool: "get_sst", timestamp: "2026-09-29T14:31:29Z" },
      { agent: "ocean", tool: "get_chlorophyll", timestamp: "2026-09-29T14:31:29Z" },
      { agent: "ocean", tool: "get_pfz", timestamp: "2026-09-29T14:31:29Z" },
      { agent: "planner", tool: "replan:pfz", timestamp: "2026-09-29T14:31:30Z" },
      { agent: "viz", tool: "llm:mock-fallback", timestamp: "2026-09-29T14:31:30Z" }
    ],
    session_id: "probe-1",
    citations: ["incois_advisories", "safety_thresholds"],
    degraded: true
  },

  /* A real but step-less response (compare intent with <2 named sites), to
     check the "no trace returned" rendering. */
  "empty-trace": {
    answer: "To compare, name two sites from: chennai, kochi, mumbai, sundarbans, visakhapatnam, vizag.. Sources: forecast_provenance, incois_advisories.",
    verdict: "info",
    reasons: [],
    trace: [],
    session_id: "probe-1",
    citations: ["forecast_provenance", "incois_advisories"],
    degraded: false
  },

  error: "__ERROR__"
};

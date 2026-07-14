---
title: "Map Site Picker for the Vietnam DPPA Web App"
date: "2026-07-06"
type: "brainstorm"
depth: "standard"
source_request: "Integrate map/QGIS functionality into the UI of the Vietnam DPPA web app"
slug: "map-site-picker-webapp"
---

# Brainstorm: Map Site Picker for the Vietnam DPPA Web App

## Problem & Why Now
Entering a deal in `/deals/new` requires typing raw latitude/longitude by hand. Users
rarely have exact coordinates memorized; they know a place ("Bac Ninh industrial park",
"near the Ninh Sim site") and want to point at it. A map-based site picker removes the
most error-prone step of deal entry and gives geographic context (where the site sits
relative to known developer projects) that the current numeric fields cannot. "QGIS" in
the original request was shorthand for mapping — no QGIS tooling is wanted or needed.

## Current vs Desired State
- **Current state:** FastAPI + Jinja2 server-rendered app at
  `src/python/reopt_pysam_vn/webapp/` (vanilla JS, no bundler, Plotly via CDN).
  `/deals/new` has plain `site.latitude` / `site.longitude` number inputs and a manual
  `site.region` dropdown (north/central/south), prefilled from
  `scenarios/templates/*.json`. The repo has **no** GeoJSON/shapefiles/QGIS files; the
  only geo data is point lat/lon: 5 project records in `data/projects/*.json`
  (lat/lon, province, technology, capacity, strike, status — schema at
  `data/projects/catalog_schema.json`) and per-run `deal_config.json` site coords.
- **Desired state:** An interactive Leaflet map embedded in the Site section of
  `/deals/new` with two-way sync to the lat/lon fields, auto-derived region,
  Nominatim place search, and catalog-project reference markers; plus a compact
  read-only context map on `/runs/{id}` showing the modeled site and nearby projects.
- **Key repo surfaces:** `webapp/templates/base.html` (CDN tags), `templates/new_deal.html`
  (form + picker), `templates/run.html` (context map), `webapp/routes/api.py`
  (new `/api/projects`), `webapp/routes/pages.py`, `webapp/static/app.js` (or a new
  `static/map.js`), `webapp/forms.py` (pattern for reading JSON assets),
  `data/projects/*.json` (marker source).

## Resolved Decisions
- **DEC-001:** Primary feature is a **site picker inside the deal form** (`/deals/new`),
  not a standalone map page or GIS workspace — it directly improves the existing
  core workflow.
- **DEC-002:** **No QGIS dependency.** Pure web map; "QGIS" was shorthand for mapping.
- **DEC-003:** **Leaflet via CDN** (one CSS + one JS tag) with OSM raster tiles —
  consistent with the app's existing CDN posture (Plotly), best-in-class for
  click/drag marker picking; Plotly map traces rejected as display-oriented.
- **DEC-004:** **Two-way sync, inline map**: map embedded in the Site section; click or
  drag marker → lat/lon inputs update; typing coordinates → marker moves; template
  prefills (and `?from={run_id}` duplication) position the marker on load.
- **DEC-005:** **Project overlay markers**: plot `data/projects/*.json` on the picker
  with tooltips (name, technology, MW, indicative strike) via a new read-only
  `/api/projects` endpoint. Display-only — no click-to-prefill (see Out of Scope).
- **DEC-006:** **Auto-set `site.region` from latitude bands** (≥20°N → north,
  14–20°N → central, <14°N → south), user can still override the dropdown manually.
  Province polygons rejected — no geometry in repo and the enum is only 3 values.
- **DEC-007:** **Nominatim free-text search box** on the picker (OSM public API, no
  key; acceptable usage for a localhost single-user tool) to jump to places.
- **DEC-008:** **Run-page context map in scope**: compact non-interactive Leaflet map
  on `run.html` showing the run's site plus catalog projects, reusing the same
  setup and endpoint.
- **DEC-009:** Tile source is standard OSM (`tile.openstreetmap.org`) with required
  attribution; default view centered on Vietnam (~c. 16°N 106°E, zoom ~5) when no
  prefill coords exist.
- **DEC-010:** **Graceful degradation**: if tiles/CDN/Nominatim are unreachable, the
  numeric lat/lon fields and region dropdown must keep working unchanged — the map is
  an enhancement layered on the existing form, never a gate to submission.
- **DEC-011:** Verification: pytest for the backend pieces (`/api/projects` contract,
  latitude-band region derivation if implemented server-side or as a tested pure
  function) following the webapp's existing test pattern; end-to-end picker behavior
  verified in the browser (Claude-in-Chrome / `/run`).
- **DEC-012:** No new persistence: `/api/projects` reads `data/projects/*.json`
  directly (mirroring how `forms.py` reads scenario templates); no database, no
  new file formats.

## Assumptions & Constraints
- **ASM-001:** Outbound internet access is available at runtime (already assumed for
  the Plotly CDN); OSM tiles and Nominatim add two more external endpoints.
- **ASM-002:** Single local user — Nominatim/OSM usage-policy limits are not a concern.
- **ASM-003:** The 3-value region enum's latitude-band boundaries (20°N / 14°N) are an
  acceptable approximation of how the model uses `site.region`.
- **CON-001:** No frontend build tooling — vanilla JS + CDN tags only, matching the
  existing webapp convention.
- **CON-002:** No polygon/line geometry exists in the repo; nothing in this feature may
  depend on province boundaries, grid lines, or substations.
- **CON-003:** Localhost-only, no auth — endpoints stay read-only and unauthenticated
  like the rest of `/api`.

## Approaches Considered
- **Chosen:** Leaflet-via-CDN inline picker with two-way field sync, latitude-band
  region derivation, Nominatim search, catalog-project overlay, plus a read-only
  run-page context map — maximal workflow value with zero new build infrastructure.
- **ALT-001:** Standalone "Projects map" page from the catalog — deferred; the picker
  already surfaces the catalog as an overlay, and a dedicated page can follow later.
- **ALT-002:** Plotly scattermap (zero new deps) — rejected; poor fit for
  click/drag-to-pick interactions.
- **ALT-003:** QGIS-authored GeoJSON layers (provinces, grid) rendered as overlays —
  rejected for now; no source geometry exists and the picker doesn't need it.
- **ALT-004:** Full GIS workspace / QGIS Server integration — rejected; heavy
  infrastructure for a localhost single-user tool.

## Out of Scope
- Click-a-project-marker-to-prefill-the-deal (templating from catalog records).
- Province polygons, transmission lines, substations, or any layered GIS overlays.
- Maps on `/compare`.
- Offline/bundled tiles for restricted-network deployment.
- Any QGIS files, plugins, or server components.

## Open Questions
1. **Q-001:** OSM tiles render international boundaries per OSM defaults; does the
   South China Sea / island labeling matter if run-page map screenshots end up in
   Vietnam-facing client decks?
   - **Recommended default:** Ignore for this internal localhost tool; revisit tile
     style only if screenshots go client-facing.
   - **Why this matters:** Boundary depiction is politically sensitive in Vietnam;
     switching tile providers later is a one-line change but worth flagging.

## Suggested Next Step
Run `/plan map-site-picker-webapp` to turn this into a multi-phase implementation plan.

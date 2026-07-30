---
title: "Map Site Picker for the Vietnam DPPA Web App"
date: "2026-07-06"
status: "complete — PHASE-01..04 shipped (commits 8a61950, d2f6697, d0b70cf, fd8ceaf): webapp/projects.py + GET /api/projects, static/map.js site picker, run-page context map, 50/50 webapp tests green per activeContext.md"
request: "map-site-picker-webapp"
plan_type: "multi-phase"
research_inputs:
  - "research/2026-07-06_map-site-picker-webapp-brainstorm.md"
---

# Plan: Map Site Picker for the Vietnam DPPA Web App

## Objective
Replace blind lat/lon typing in the `/deals/new` form with an interactive Leaflet
site picker (two-way field sync, auto-derived region, Nominatim place search,
catalog-project reference markers), and add a compact read-only context map to the
run results page. No QGIS dependency — pure web map, staying within the app's
vanilla-JS + CDN conventions.

## Context Snapshot
- **Current state:** FastAPI + Jinja2 webapp at `src/python/reopt_pysam_vn/webapp/`.
  `/deals/new` (`templates/new_deal.html` lines 53–56) has plain number inputs
  `site.latitude` / `site.longitude` and a manual `site.region` dropdown
  (north/central/south), prefilled from `scenarios/templates/*.json` via
  `forms.template_defaults()` or duplicated from a prior run via `?from={run_id}`.
  The only frontend JS is `static/app.js` (vanilla) plus Plotly from
  `cdn.plot.ly` in `templates/base.html` line 7. Five project records with
  `location: {lat, lon, province, region}` exist in `data/projects/*.json`
  (schema: `data/projects/catalog_schema.json`). No GeoJSON/polygon geometry
  anywhere in the repo. `pages.run_detail()` renders `run.html` with only
  `run_id`, `status`, `view` — it does not pass the deal config (site coords).
- **Desired state:** Inline Leaflet map in the Site section of `new_deal.html`
  synced both ways with the lat/lon inputs; latitude-band auto-set of the region
  dropdown; Nominatim search box; catalog projects plotted with tooltips from a
  new `GET /api/projects`; and a small non-interactive map card on `run.html`
  showing the run's site plus catalog projects. Plain fields keep working if
  tiles/CDN/Nominatim are unreachable.
- **Key repo surfaces:** `webapp/templates/base.html` (CDN tags / head block),
  `webapp/templates/new_deal.html`, `webapp/templates/run.html`,
  `webapp/routes/api.py`, `webapp/routes/pages.py`, `webapp/forms.py` (pattern
  for reading repo JSON assets), new `webapp/projects.py`, new
  `webapp/static/map.js`, `data/projects/*.json`, tests under
  `tests/python/webapp/` (existing `conftest.py` provides the app/client fixture
  pattern).
- **Out of scope:** click-a-project-to-prefill deal fields; province polygons,
  transmission lines, or any layered GIS overlays; maps on `/compare`;
  offline/bundled tiles; any QGIS files or server components.

## Research Inputs
- `research/2026-07-06_map-site-picker-webapp-brainstorm.md` — fixes all
  high-leverage decisions (DEC-001…012): picker-in-form as primary feature,
  Leaflet via CDN over Plotly maps, two-way inline sync, latitude-band region
  derivation (≥20°N north, 14–20°N central, <14°N south), Nominatim search,
  project-marker overlay via read-only endpoint, run-page context map in scope,
  graceful degradation, pytest + browser verification split.

## Assumptions and Constraints
- **ASM-001:** Outbound internet is available at runtime (already true for the
  Plotly CDN); OSM tiles (`tile.openstreetmap.org`) and Nominatim
  (`nominatim.openstreetmap.org`) are two additional external endpoints,
  acceptable for a localhost single-user tool.
- **ASM-002:** Latitude bands 20°N / 14°N are an acceptable approximation for the
  3-value `site.region` enum; the user can always override the dropdown.
- **CON-001:** No frontend build tooling — vanilla JS + CDN `<script>`/`<link>`
  tags only; no npm, no bundler.
- **CON-002:** Nothing may depend on polygon/line geometry; only point lat/lon
  exists in the repo.
- **CON-003:** New endpoints are read-only and unauthenticated, matching the rest
  of `/api` on the localhost-only app.
- **DEC-001:** Leaflet ~1.9.x pinned via CDN (one CSS + one JS tag with SRI
  hashes), loaded only on pages that render a map (via a Jinja head block), not
  globally.
- **DEC-002:** `/api/projects` reads `data/projects/*.json` directly (mirroring
  `forms.py`'s template reader); no new persistence.
- **DEC-003:** The map is an enhancement layer: form submission must not depend
  on Leaflet/Nominatim/tiles loading successfully.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Projects catalog backend: loader + `GET /api/projects` (TDD) | None | `webapp/projects.py`, endpoint in `routes/api.py`, `tests/python/webapp/test_projects.py` |
| PHASE-02 | Leaflet site picker in `/deals/new` with sync, region bands, search, markers | PHASE-01 | `static/map.js`, edits to `base.html` + `new_deal.html` |
| PHASE-03 | Read-only context map on `/runs/{run_id}` | PHASE-01, PHASE-02 | Edits to `routes/pages.py` + `run.html`, reuse of `map.js` |
| PHASE-04 | End-to-end verification and degradation checks | PHASE-02, PHASE-03 | Passing pytest suite, browser-verified flows, updated `activeContext.md` review section |

## Detailed Phases

### PHASE-01 - Projects Catalog Backend
**Goal**
Expose the `data/projects/*.json` catalog as a stable read-only JSON endpoint the
map front-end can fetch, with tests written first.

**Tasks**
- [x] TASK-01-01: Write failing tests in `tests/python/webapp/test_projects.py`
      (reuse the app/client fixture from `tests/python/webapp/conftest.py`):
      `GET /api/projects` returns 200 with `{"projects": [...]}`; each item has
      `project_id`, `name`, `technology`, `capacity_mw`, `status`,
      `indicative_strike_usc_kwh`, and `location.{lat,lon,province,region}`;
      `catalog_schema.json` is excluded; records missing `location.lat/lon` are
      skipped, not fatal. Run and confirm red.
- [x] TASK-01-02: Implement `src/python/reopt_pysam_vn/webapp/projects.py` with
      `list_projects() -> List[Dict]`: glob `data/projects/*.json` (resolve the
      repo root the same way `forms.py` does with
      `Path(__file__).resolve().parents[4]`), skip `catalog_schema.json` and any
      file without numeric `location.lat`/`location.lon`, and return the fields
      asserted in TASK-01-01 (pass through the tooltip-relevant subset, not the
      whole record).
- [x] TASK-01-03: Add `@router.get("/projects")` in
      `src/python/reopt_pysam_vn/webapp/routes/api.py` returning
      `{"projects": list_projects()}`. Run tests and confirm green.

**Files / Surfaces**
- `src/python/reopt_pysam_vn/webapp/projects.py` - new loader module.
- `src/python/reopt_pysam_vn/webapp/routes/api.py` - new GET route.
- `tests/python/webapp/test_projects.py` - new test module (red first).
- `data/projects/*.json`, `data/projects/catalog_schema.json` - read-only source.

**Dependencies**
- None (pure backend; runs in the repo `.venv`, Python 3.12).

**Exit Criteria**
- [ ] `pytest tests/python/webapp/test_projects.py` passes (was red before
      implementation).
- [ ] `curl http://127.0.0.1:8000/api/projects` returns the 5 catalog projects
      with lat/lon.

**Phase Risks**
- **RISK-01-01:** Repo-root path resolution differs when installed vs editable.
  Mitigation: copy the exact `parents[4]` pattern proven in `forms.py` and cover
  it with the endpoint test (which exercises the real path).

### PHASE-02 - Leaflet Site Picker in the Deal Form
**Goal**
Embed an interactive Leaflet map in the Site section of `new_deal.html` with
two-way lat/lon sync, latitude-band region auto-set, Nominatim search, and
catalog-project reference markers.

**Tasks**
- [x] TASK-02-01: In `templates/base.html`, add `{% block head_extra %}{% endblock %}`
      inside `<head>` so map pages can inject Leaflet CSS/JS without loading it
      globally.
- [x] TASK-02-02: Create `src/python/reopt_pysam_vn/webapp/static/map.js`
      (vanilla JS) exposing two initializers on `window`:
      `initSitePicker(opts)` and `initContextMap(opts)`. `initSitePicker`:
      - creates the map with OSM tiles + attribution; if `window.L` is
        undefined (CDN blocked), silently do nothing (DEC-003);
      - places a draggable marker at the current lat/lon input values, or
        centers on Vietnam (16.0°N, 106.0°E, zoom 5) when the inputs are empty;
      - map click and marker dragend → write 4-decimal values into
        `#site_latitude` / `#site_longitude` and update the region dropdown via
        `regionForLatitude(lat)` (≥20 → "north", ≥14 → "central", else
        "south"), leaving the user free to re-override the dropdown;
      - `input`/`change` on the lat/lon fields → move the marker/center;
      - fetches `/api/projects` and renders distinct (e.g. `L.circleMarker`)
        reference markers with `bindPopup` tooltips: name, technology,
        capacity_mw, indicative_strike_usc_kwh, status; fetch failure is
        non-fatal;
      - wires a small search input + button to Nominatim
        (`https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=vn&q=...`),
        panning/placing the marker on the top hit; errors show inline text, not
        an alert.
- [x] TASK-02-03: In `templates/new_deal.html`: add the Leaflet CSS/JS CDN tags
      (pinned 1.9.x with SRI) inside `{% block head_extra %}`; add a
      `<div id="site-map">` (~360px tall) plus the search input/button and a
      one-line hint ("Click the map or drag the marker to set coordinates")
      inside the Site section; load `/static/map.js` and call
      `initSitePicker(...)` after the form markup. Add minimal height/width CSS
      (inline style block in the template or `base.html`).
- [x] TASK-02-04: Manually verify prefill paths: template prefill
      (`/deals/new`), duplication (`/deals/new?from={run_id}`), and empty-coords
      fallback all position the marker correctly; typing coordinates moves the
      marker; picking a point near 21°N sets region "north", near 16°N
      "central", near 11°N "south".

**Files / Surfaces**
- `src/python/reopt_pysam_vn/webapp/templates/base.html` - add head block.
- `src/python/reopt_pysam_vn/webapp/templates/new_deal.html` - map container,
  search UI, CDN tags, init call (Site section, currently lines 33–57).
- `src/python/reopt_pysam_vn/webapp/static/map.js` - new; all map logic lives
  here (shared with PHASE-03).

**Dependencies**
- PHASE-01 (`/api/projects` for the overlay markers).
- External: Leaflet CDN (unpkg or leafletjs CDN), OSM tile server, Nominatim.

**Exit Criteria**
- [ ] Picker renders in `/deals/new`; click/drag/type sync works both ways;
      region auto-sets per band; the 5 catalog projects appear with tooltips;
      search "Bac Ninh" pans the map.
- [ ] With the Leaflet script tag manually blocked, the form still submits a
      valid deal using typed coordinates (DEC-003).
- [ ] Existing suite still green: `pytest tests/python/webapp/`.

**Phase Risks**
- **RISK-02-01:** Two-way sync feedback loop (field event moves marker, which
  fires an update back into the field). Mitigation: only write fields from map
  events and only move the marker from field events; never re-dispatch input
  events programmatically.
- **RISK-02-02:** Nominatim rate limits / no results. Mitigation: single-shot
  search on button/Enter (no autocomplete), `limit=1&countrycodes=vn`, inline
  "no results" message.

### PHASE-03 - Context Map on the Run Page
**Goal**
Show a compact, non-interactive map on `/runs/{run_id}` with the modeled site and
catalog projects, reusing `map.js`.

**Tasks**
- [x] TASK-03-01: In `routes/pages.py` `run_detail()`, also fetch
      `storage.get_deal_config(run_id)` (tolerating `KeyError` → `{}`) and pass
      `site = deal_config.get("site", {})` into the `run.html` context.
- [x] TASK-03-02: In `templates/run.html`: add Leaflet CDN tags via
      `{% block head_extra %}`; add a `.card` with `<div id="context-map">`
      (~280px tall) rendered only when `site.latitude` and `site.longitude` are
      present; call `initContextMap({lat, lon, ...})` from `map.js` —
      non-interactive (dragging/scrollWheelZoom/tap disabled), site marker
      highlighted, catalog projects from `/api/projects` as muted markers,
      auto-fit bounds to site + projects.
- [x] TASK-03-03: Add a small pytest in `tests/python/webapp/` (extend an
      existing page-test module or add `test_run_page_map.py`) asserting the
      run page for a completed run contains the `context-map` container and
      that a run whose deal config lacks coordinates renders without it
      (write red first per TDD).

**Files / Surfaces**
- `src/python/reopt_pysam_vn/webapp/routes/pages.py` - pass site coords to the
  template (currently omits deal config).
- `src/python/reopt_pysam_vn/webapp/templates/run.html` - map card + init call.
- `src/python/reopt_pysam_vn/webapp/static/map.js` - `initContextMap` (written
  in PHASE-02, exercised here).

**Dependencies**
- PHASE-01 (projects endpoint), PHASE-02 (`map.js`, head block).

**Exit Criteria**
- [ ] A completed run with site coords shows the context map with the site and
      the 5 projects; a run without coords shows no map card and no JS errors.
- [ ] New page test green; full `pytest tests/python/webapp/` green.

**Phase Risks**
- **RISK-03-01:** Runs created before this feature may lack `site.latitude` /
  `site.longitude` in `deal_config.json`. Mitigation: the template guard in
  TASK-03-02 makes the map strictly conditional; covered by TASK-03-03.

### PHASE-04 - End-to-End Verification
**Goal**
Prove the whole flow works in a real browser, including degradation paths, and
close out the plan bookkeeping.

**Tasks**
- [x] TASK-04-01: Run the full suite: `pytest tests/python/webapp/` from the
      repo `.venv`.
- [x] TASK-04-02: Start the app (`uvicorn reopt_pysam_vn.webapp:app --host
      127.0.0.1 --port 8000` from `.venv`) and drive it in the browser
      (Claude-in-Chrome / `/run`): complete a full deal submission where the
      coordinates were set by clicking the map; confirm the created run's
      `deal_config.json` carries the picked lat/lon and derived region.
- [x] TASK-04-03: Degradation checks: block/omit the Leaflet CDN tag and confirm
      the form still submits with typed coordinates; kill network to Nominatim
      and confirm search fails inline without breaking the picker.
- [x] TASK-04-04: Screenshot the run-page context map (deck-ready) and add the
      review/results section to `activeContext.md` per project convention.

**Files / Surfaces**
- `activeContext.md` - plan checklist + review section (project convention).
- No product-code changes expected; fixes loop back into PHASE-02/03 tasks.

**Dependencies**
- PHASE-02, PHASE-03 complete; running `.venv` (Python 3.12) with `[webapp]`
  extras installed; outbound network for tiles.

**Exit Criteria**
- [ ] Full pytest suite green; browser flow completed end-to-end with evidence
      (screenshot + the created run's `deal_config.json` values).
- [ ] Both degradation checks pass.

**Phase Risks**
- **RISK-04-01:** Browser automation flakiness with map tiles loading slowly.
  Mitigation: assert on marker/field state rather than tile pixels; allow a
  settle delay before screenshots.

## Verification Strategy
- **TEST-001:** `pytest tests/python/webapp/test_projects.py` — endpoint
  contract (PHASE-01, red→green).
- **TEST-002:** `pytest tests/python/webapp/` — full webapp suite after each
  phase; includes the PHASE-03 run-page container test.
- **MANUAL-001:** Browser walkthrough of `/deals/new`: click-to-set, drag,
  type-to-move, region banding at 21/16/11°N, project tooltips, Nominatim
  search (PHASE-02/04).
- **MANUAL-002:** Degradation: Leaflet CDN blocked → form still submits;
  Nominatim unreachable → inline error only (PHASE-04).
- **OBS-001:** Browser console clean of uncaught JS errors on `/deals/new`,
  `/runs/{id}` (with and without site coords), and all non-map pages.

## Risks and Alternatives
- **RISK-001:** External runtime dependencies (OSM tiles, Nominatim, Leaflet
  CDN) can be slow or blocked. Mitigation: DEC-003 graceful degradation — the
  numeric fields and region dropdown remain fully functional without the map.
- **RISK-002:** OSM tile rendering of South China Sea boundaries/islands could
  be sensitive if run-page screenshots reach Vietnam-facing client decks.
  Mitigation: accepted for the internal tool (brainstorm Q-001 default); tile
  provider is a one-line change in `map.js` if needed later.
- **ALT-001:** Plotly map traces (zero new deps) — rejected: poor fit for
  click/drag picking interactions.
- **ALT-002:** Province-polygon GeoJSON for exact region derivation — rejected:
  no geometry in the repo, 3-value enum doesn't justify sourcing ~MBs of
  boundaries.
- **ALT-003:** Standalone projects-map page — deferred: the picker overlay
  already surfaces the catalog; a dedicated page can follow later.

## Grill Me
1. **Q-001:** Does OSM's default boundary/island rendering matter for run-page
   map screenshots that may end up in Vietnam-facing client decks?
   - **Recommended default:** No — accept OSM defaults for this internal
     localhost tool.
   - **Why this matters:** Boundary depiction is politically sensitive in
     Vietnam; a client-facing posture would warrant choosing a different tile
     style before screenshots circulate.
   - **If answered differently:** Add a tile-provider decision to PHASE-02
     (e.g., a neutral basemap such as Carto Voyager) — a one-line tile-URL
     change plus attribution update; no other plan changes.

## Suggested Next Step
Answer Q-001 (or accept the default), then begin PHASE-01 with the failing
`test_projects.py` tests in the repo `.venv`.

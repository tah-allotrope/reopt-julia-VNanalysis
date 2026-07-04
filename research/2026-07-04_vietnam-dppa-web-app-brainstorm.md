---
title: "Vietnam DPPA Web App"
date: "2026-07-04"
type: "brainstorm"
depth: "deep"
source_request: "a web app interface for this repo that exposes the Vietnam analytics functionality (REopt/PySAM DPPA modeling) with ease of use for non-technical users"
slug: "vietnam-dppa-web-app"
---

# Brainstorm: Vietnam DPPA Web App

## Problem & Why Now
<!-- seeds /plan ## Objective -->
The repo's Vietnam DPPA analytics (`reopt_pysam_vn.analysis`: onsite REopt PV+BESS screening, offsite DPPA developer finance + CfD settlement, combined decision) are only reachable via a Python CLI and JSON configs. That locks out non-technical users at Allotrope: every deal screen requires someone comfortable with a terminal, `DealConfig` JSON, and the venv. An internal web app closes the loop — form → solve → results in a browser — so deal screens stop bottlenecking on the one person who can drive the CLI. It is also the deliberate first step toward the "DPPA Deal Screener" product sketched in `research/2026-04-26_commercial-product-ideas.md` (Idea 1), without committing to SaaS scope yet.

## Current vs Desired State
<!-- seeds /plan ## Context Snapshot -->
- **Current state:** Clean analysis API exists — `run_onsite(deal_config)` / `run_offsite_dppa(deal_config)` in `src/python/reopt_pysam_vn/analysis/` with a `DealConfig` JSON contract (`data/schemas/deal_config.schema.json`) and CLI (`python -m reopt_pysam_vn.analysis`). Solves go through the NREL REopt API (`reopt/preprocess.py: run_vietnam_reopt`, key in `NREL_API.env`) or a local Julia path. Vietnam policy data is versioned JSON under `data/vietnam/` (EVN tariffs, Decree 57 export rules, tech costs, regime registry) selected via `manifest.json`. Outputs land as JSON in `artifacts/results/` plus HTML reports (`integration/generate_html_report.py`). **No web/API/UI layer exists** — no Flask/FastAPI/Streamlit anywhere; deps are lean (pandas, matplotlib, requests, nrel-pysam, openpyxl) on a uv-managed Python 3.12 venv (Windows).
- **Desired state:** A FastAPI app served locally (`uvicorn`, localhost) with Jinja2-rendered pages: guided deal form seeded from scenario templates, CSV/xlsx load-profile upload, background solve via the NREL REopt API with polling, a native results page with interactive Plotly charts and JSON/HTML downloads, a run-history index with reopen/clone-and-edit, and a two-run side-by-side comparison view. Runs persist as config+result JSON under a git-ignored `artifacts/webapp/runs/`.
- **Key repo surfaces:** `src/python/reopt_pysam_vn/analysis/` (`onsite.py`, `offsite_dppa.py`, `types.py`, `__main__.py`), `reopt/preprocess.py` (`run_vietnam_reopt`, `apply_vietnam_defaults`), `data/schemas/deal_config.schema.json`, `data/vietnam/*.json` + `manifest.json`, `scenarios/templates/*.json` (4 archetypes), `data/vietnam/reference_load_shapes/`, `integration/generate_html_report.py`, `examples/samsung-ttc_combined-decision.example.json` (golden parity target), `NREL_API.env`.

## Resolved Decisions
<!-- the grilled Q&A; each one keeps /plan's Grill Me empty -->
- **DEC-001:** Audience is an internal tool for the user/Allotrope — no auth/billing/multi-tenant scope; can evolve toward the Deal Screener product later.
- **DEC-002:** Day-one job is the full deal screen: enter/upload a deal, run onsite and/or offsite DPPA, see the report in the browser — the whole DealConfig loop without a terminal.
- **DEC-003:** Solve backend is the NREL REopt API (reusing `run_vietnam_reopt`) — no Julia toolchain on the serving path; runs take tens of seconds to minutes.
- **DEC-004:** Stack is a FastAPI backend + simple HTML/JS frontend — a real API layer usable by scripts later, chosen over Streamlit/Dash.
- **DEC-005:** Long runs handled with in-process background jobs + polling: `POST /runs` returns a job ID; frontend polls `GET /runs/{id}`. No Celery/Redis.
- **DEC-006:** Deal input is a guided form seeded by templates — pick an archetype from `scenarios/templates/` + `vn_deal_defaults_2026`, then edit structured sections (site, plant, contract, finance) with Vietnam defaults prefilled.
- **DEC-007:** Load profile enters via CSV/Excel upload only (no reference-shape picker at launch).
- **DEC-008:** Launch analysis scope is onsite + offsite DPPA + combined decision (mode-selectable, matching the CLI). Strike-sweep views, regime toggles, and sensitivity sweeps are deferred to phase 2.
- **DEC-009:** Results shown on a native results page — headline metrics (NPV, sizing, delivered fraction, IRR/DSCR), key charts, plus download buttons for raw result JSON and the existing HTML report.
- **DEC-010:** Persistence is filesystem JSON under git-ignored `artifacts/webapp/runs/` (config + result per run), matching the repo's artifacts convention; no database.
- **DEC-011:** Day one includes a run-history page: list (name, date, mode, headline metric), reopen results, and "duplicate as new deal" clone-and-edit.
- **DEC-012:** Frontend is Jinja2 server-rendered templates + a small vanilla-JS file (polling, form dynamics). No build step, no npm.
- **DEC-013:** Charts are client-side interactive (Plotly chosen for 8760-hour dispatch series and metric charts), loaded via CDN — acceptable for an internal localhost tool.
- **DEC-014:** Hosting is localhost on the user's machine: `uvicorn` in the repo venv, bound to 127.0.0.1.
- **DEC-015:** No access control at launch (localhost-only); add a password gate only if binding beyond localhost later.
- **DEC-016:** Upload parsing is deliberately simple: one column of 8760 hourly kW values in CSV or basic .xlsx, with length/units validation. Full `.xlsm` workbook extraction (`extract_excel_inputs.py`) is out of scope for v1.
- **DEC-017:** Vietnam assumptions get key overrides only: defaults load from the versioned `data/vietnam/` JSON (pinned via `manifest.json`); the form exposes the handful that move deals (capex, discount rate, PPA/strike terms, escalations); the rest shown read-only.
- **DEC-018:** Two-run side-by-side comparison IS in v1 scope (user upgraded from the recommended phase-2 deferral): a two-column compare of headline metrics for any two saved runs.
- **DEC-019:** Acceptance bar is golden parity + cold-start demo: the Samsung/TTC config run through the web app matches `examples/samsung-ttc_combined-decision.example.json`, AND a fresh deal goes form → solve → results without touching a terminal.
- **DEC-020:** (self-resolved from repo) NREL key loaded from the existing `NREL_API.env` / env vars — no new secret plumbing.
- **DEC-021:** (self-resolved) Web app lives as a subpackage `src/python/reopt_pysam_vn/webapp/` (routes, templates/, static/, jobs, storage), importing `analysis` directly; launched via `uvicorn reopt_pysam_vn.webapp:app`.
- **DEC-022:** (self-resolved) Concurrency capped at one active solve at a time (single-user tool; avoids NREL rate-limit surprises); additional submissions queue in-process.
- **DEC-023:** (self-resolved, per user's global TDD rule) Backend built red/green with FastAPI `TestClient`; solve calls mocked with recorded NREL responses so tests don't hit the network.

## Assumptions & Constraints
<!-- seeds /plan ## Assumptions and Constraints -->
- **ASM-001:** The NREL REopt API key in `NREL_API.env` remains valid and rate limits tolerate interactive single-user usage (roughly a handful of solves per hour).
- **ASM-002:** CDN access (Plotly) is acceptable since the tool is internal and browser-side only; pages should degrade to metric tables if the CDN is unreachable.
- **ASM-003:** The `DealConfig` schema and `analysis` package contracts are stable enough to build a form against; schema drift is handled by regenerating the form from `deal_config.schema.json` where practical.
- **ASM-004:** Single user on Windows, running inside the existing uv-managed Python 3.12 `.venv` (PySAM only exists there — see repo memory).
- **CON-001:** No new heavy infrastructure: no database, no Redis/Celery, no npm build step, no Julia on the serving path.
- **CON-002:** The web app must not fork analytics logic — it calls `run_onsite`/`run_offsite_dppa` and `run_vietnam_reopt` as-is; any needed changes go into the library, not the webapp.
- **CON-003:** Deprecated `integration/dppa_case_*.py` engines must not be wired into the app (repo README directs new work to `analysis`).
- **CON-004:** Solve latency (tens of seconds to minutes via NREL API) means every solve-triggering interaction must be async with visible status; no blocking requests.

## Approaches Considered
<!-- seeds /plan ## Risks and Alternatives -->
- **Chosen:** FastAPI + Jinja2/vanilla-JS internal app wrapping `reopt_pysam_vn.analysis`, NREL-API solves in background tasks, filesystem persistence — a real API layer with minimal new surface, aligned with the repo's JSON-artifact conventions and a credible stepping stone to the Deal Screener product.
- **ALT-001:** Streamlit — fastest to ship for pure-Python internal tools, but rejected by the user in favor of a real API layer that scripts and a future client-facing frontend can also call.
- **ALT-002:** Local Julia REopt.jl solve backend — no network dependency but 3–8 min compiles, 5–10 min solves, and the full Julia stack on the serving machine; rejected for v1 (NREL API is faster to wire and adequate).
- **ALT-003:** Celery/RQ + Redis job queue — robust for many users, overkill for a single-user localhost tool; in-process jobs suffice.
- **ALT-004:** Embedding the existing `generate_html_report.py` output as the results view — least code but document-shaped, not interactive; kept only as a download option.
- **ALT-005:** Full `.xlsm` workbook import via `extract_excel_inputs.py` — powerful but fragile across layouts; deferred, simple hourly-column upload chosen.

## Out of Scope
- Multi-tenant SaaS features: auth, billing, per-user accounts, cloud hosting (the Apr-26 Deal Screener product path — later).
- Strike-sweep interactive views, regime/TOU scenario toggles, and batch sensitivity sweeps (FMP, two-part tariff, adders) — phase 2 candidates.
- Local Julia solve path from the web app.
- Reference-load-shape picker and `.xlsm` workbook extraction as upload paths.
- Editing the versioned `data/vietnam/` policy files from the UI (read-only defaults + key overrides only).
- PPTX/deck generation from the app.

## Open Questions
<!-- the few that survived; seed /plan ## Grill Me. Use `None.` when fully resolved. -->
1. **Q-001:** Will teammates need to reach the app from their own machines soon (i.e., bind beyond 127.0.0.1)?
   - **Recommended default:** Ship localhost-only v1; revisit LAN binding + a shared-password gate after first real usage.
   - **Why this matters:** Binding beyond localhost makes the no-auth decision (DEC-015) unsafe and adds concurrency requirements beyond DEC-022.
2. **Q-002:** Should identical configs reuse cached solve results (hash of DealConfig → previous NREL result) instead of re-solving?
   - **Recommended default:** Yes — cheap to add on top of filesystem persistence and protects NREL rate limits; offer a "force re-solve" checkbox.
   - **Why this matters:** Affects run-storage layout and whether clone-and-edit re-runs are instant or minutes-long.

## Suggested Next Step
Run `/plan vietnam-dppa-web-app` to turn this into a multi-phase implementation plan.

"""Server-rendered pages: new-deal form, run results, run history, compare."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from reopt_pysam_vn.webapp.compare import build_compare_model
from reopt_pysam_vn.webapp.forms import list_templates, template_defaults
from reopt_pysam_vn.webapp.results_view import build_view_model

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates_engine = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter()

_PREFILL_SECTIONS = ("site", "plant", "load", "contract", "finance")


def _empty_sections(prefill: dict) -> dict:
    for section in _PREFILL_SECTIONS:
        prefill.setdefault(section, {})
    return prefill


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    storage = request.app.state.storage
    return templates_engine.TemplateResponse(request, "runs.html", {"runs": storage.list_runs()})


@router.get("/runs", response_class=HTMLResponse)
def runs_index(request: Request) -> HTMLResponse:
    storage = request.app.state.storage
    return templates_engine.TemplateResponse(request, "runs.html", {"runs": storage.list_runs()})


@router.get("/deals/new", response_class=HTMLResponse)
def new_deal_form(request: Request, from_: str | None = None, template: str | None = None) -> HTMLResponse:
    storage = request.app.state.storage
    from_run_id = request.query_params.get("from")
    tmpls = list_templates()
    default_template_id = tmpls[0]["id"] if tmpls else ""

    if from_run_id:
        try:
            prefill = dict(storage.get_deal_config(from_run_id))
        except KeyError:
            prefill = {}
        prefill.setdefault("template_id", template or default_template_id)
    else:
        template_id = template or default_template_id
        prefill = dict(template_defaults(template_id)) if template_id else {}
        prefill["template_id"] = template_id

    prefill = _empty_sections(prefill)
    return templates_engine.TemplateResponse(
        request, "new_deal.html", {"templates": tmpls, "prefill": prefill}
    )


@router.get("/runs/{run_id}", response_class=HTMLResponse)
def run_detail(run_id: str, request: Request) -> HTMLResponse:
    storage = request.app.state.storage
    try:
        status = storage.get_status(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="no such run") from exc
    result = storage.get_result(run_id)
    view = build_view_model(status.get("mode", ""), result)
    try:
        deal_config = storage.get_deal_config(run_id)
    except KeyError:
        deal_config = {}
    site = deal_config.get("site", {})
    provenance = storage.get_provenance(run_id)
    has_ledger = storage.get_ledger_csv_path(run_id) is not None
    load_cleaning = deal_config.get("load", {}).get("load_cleaning")
    return templates_engine.TemplateResponse(
        request,
        "run.html",
        {
            "run_id": run_id,
            "status": status,
            "view": view,
            "site": site,
            "provenance": provenance,
            "has_ledger": has_ledger,
            "load_cleaning": load_cleaning,
        },
    )


@router.get("/compare", response_class=HTMLResponse)
def compare_page(request: Request, a: str | None = None, b: str | None = None) -> HTMLResponse:
    storage = request.app.state.storage
    runs = storage.list_runs()
    model = None
    if a and b:
        try:
            status_a, status_b = storage.get_status(a), storage.get_status(b)
            model = build_compare_model(
                status_a.get("mode", ""), storage.get_result(a), status_b.get("mode", ""), storage.get_result(b)
            )
        except KeyError:
            model = None
    return templates_engine.TemplateResponse(
        request, "compare.html", {"runs": runs, "a_id": a, "b_id": b, "model": model}
    )

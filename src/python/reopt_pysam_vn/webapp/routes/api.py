"""JSON API: create/list/inspect runs (PHASE-01/02) and the multipart deal
submission endpoint the new-deal form posts to (PHASE-03)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.datastructures import FormData, UploadFile

from reopt_pysam_vn.analysis.types import DealConfig
from reopt_pysam_vn.webapp import service
from reopt_pysam_vn.webapp.errors import to_user_error
from reopt_pysam_vn.webapp.forms import deal_config_from_form
from reopt_pysam_vn.webapp.projects import list_projects
from reopt_pysam_vn.webapp.uploads import UploadError, parse_load_csv, parse_load_xlsx

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/projects")
def get_projects() -> dict[str, Any]:
    return {"projects": list_projects()}


def _submit_deal_config(
    request: Request,
    deal_config_dict: dict[str, Any],
    *,
    results: dict[str, Any] | None = None,
    extracted: dict[str, Any] | None = None,
    force_resolve: bool = False,
) -> str:
    storage = request.app.state.storage
    jobs = request.app.state.jobs

    try:
        deal = DealConfig.from_dict(deal_config_dict)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    run_id = storage.create_run(deal_config_dict)

    needs_background_solve = deal.mode == "onsite" and results is None
    if needs_background_solve:
        jobs.submit_solve(run_id, deal_config_dict, force_resolve=force_resolve)
    else:
        try:
            result = service.run_analysis(deal, results=results, extracted=extracted)
            storage.save_result(run_id, result)
            storage.set_status(run_id, state="done")
        except service.AnalysisError as exc:
            user_error = to_user_error(exc)
            storage.set_status(
                run_id,
                state="error",
                message=user_error["message"],
                error_code=user_error["code"],
                error_hint=user_error["hint"],
            )

    return run_id


@router.post("/runs", status_code=202)
def create_run(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    deal_config_dict = payload.get("deal_config")
    if not isinstance(deal_config_dict, dict):
        raise HTTPException(status_code=422, detail="`deal_config` is required and must be an object")
    run_id = _submit_deal_config(
        request,
        deal_config_dict,
        results=payload.get("results"),
        extracted=payload.get("extracted"),
        force_resolve=bool(payload.get("force_resolve", False)),
    )
    return {"run_id": run_id}


def _nest_form_fields(form_data: FormData) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in form_data:
        if key in ("load_file", "extracted_file", "force_resolve"):
            continue
        value: Any = form_data.get(key)
        if value == "" or value is None:
            continue
        if isinstance(value, str):
            try:
                value = float(value)
            except ValueError:
                pass
        parts = key.split(".")
        node = result
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return result


@router.post("/deals", status_code=202)
async def create_deal(request: Request) -> dict[str, Any]:
    """Multipart submission from the guided new-deal form (DEC-006/007/016)."""
    form_data = await request.form()

    load_file = form_data.get("load_file")
    loads_kw = None
    if isinstance(load_file, UploadFile) and load_file.filename:
        content = await load_file.read()
        try:
            if load_file.filename.lower().endswith(".xlsx"):
                loads_kw = parse_load_xlsx(content)
            else:
                loads_kw = parse_load_csv(content)
        except UploadError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    if loads_kw is None:
        raise HTTPException(status_code=422, detail="a load-profile file (CSV or .xlsx) is required")

    extracted = None
    extracted_file = form_data.get("extracted_file")
    if isinstance(extracted_file, UploadFile) and extracted_file.filename:
        import json

        content = await extracted_file.read()
        try:
            extracted = json.loads(content.decode("utf-8-sig"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise HTTPException(status_code=422, detail=f"invalid extracted-inputs JSON: {exc}") from exc

    nested = _nest_form_fields(form_data)
    try:
        deal_config_dict = deal_config_from_form(nested, loads_kw=loads_kw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    force_resolve = form_data.get("force_resolve") in ("on", "true", "1")
    run_id = _submit_deal_config(request, deal_config_dict, extracted=extracted, force_resolve=force_resolve)
    return {"run_id": run_id}


@router.get("/runs")
def list_runs(request: Request) -> dict[str, Any]:
    storage = request.app.state.storage
    return {"runs": storage.list_runs()}


@router.get("/runs/{run_id}")
def get_run(run_id: str, request: Request) -> dict[str, Any]:
    storage = request.app.state.storage
    try:
        status = storage.get_status(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="no such run") from exc
    return {"status": status, "result": storage.get_result(run_id)}


@router.get("/runs/{run_id}/result.json")
def download_result(run_id: str, request: Request) -> JSONResponse:
    storage = request.app.state.storage
    try:
        storage.get_status(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="no such run") from exc
    result = storage.get_result(run_id)
    if result is None:
        raise HTTPException(status_code=409, detail="run has no result yet")
    return JSONResponse(
        content=result,
        headers={"Content-Disposition": f'attachment; filename="{run_id}_result.json"'},
    )


@router.get("/runs/{run_id}/report.html")
def download_report(run_id: str, request: Request) -> HTMLResponse:
    storage = request.app.state.storage
    try:
        storage.get_status(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="no such run") from exc
    result = storage.get_result(run_id)
    if result is None:
        raise HTTPException(status_code=409, detail="run has no result yet")

    from reopt_pysam_vn.webapp.results_view import render_standalone_report_html

    html = render_standalone_report_html(run_id, storage.get_deal_config(run_id), result)
    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": f'attachment; filename="{run_id}_report.html"'},
    )

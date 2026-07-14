"""PHASE-01: analyst-facing error taxonomy."""

from reopt_pysam_vn.webapp.errors import to_user_error
from reopt_pysam_vn.webapp.service import MissingInputsError, OrchestratorNotRegisteredError


def test_missing_inputs_error_keeps_its_message():
    exc = MissingInputsError("offsite_dppa analysis needs pre-solved `extracted` inputs")
    err = to_user_error(exc)
    assert err["code"] == "MISSING_INPUTS"
    assert err["message"] == str(exc)
    assert err["hint"]


def test_orchestrator_not_registered_keeps_its_message():
    exc = OrchestratorNotRegisteredError("no offsite orchestrator registered for case 'X'")
    err = to_user_error(exc)
    assert err["code"] == "NO_ORCHESTRATOR"
    assert err["message"] == str(exc)


def test_no_api_key_runtime_error_gets_generic_message():
    exc = RuntimeError(
        "NREL API key not found. Set NREL_DEVELOPER_API_KEY env var or create "
        "NREL_API.env with API_KEY_NAME=<key>."
    )
    err = to_user_error(exc)
    assert err["code"] == "NO_API_KEY"
    assert err["message"] == "No NREL API key configured."


def test_solve_failure_runtime_error_keeps_its_message():
    exc = RuntimeError("REopt job failed with status: infeasible. Messages: {}")
    err = to_user_error(exc)
    assert err["code"] == "SOLVER_ERROR"
    assert "infeasible" in err["message"]


def test_timeout_error_keeps_its_message():
    exc = TimeoutError("REopt job abc-123 did not complete within 600s")
    err = to_user_error(exc)
    assert err["code"] == "SOLVER_ERROR"
    assert "abc-123" in err["message"]


def test_unexpected_exception_gets_generic_message():
    exc = KeyError("some_internal_key")
    err = to_user_error(exc)
    assert err["code"] == "INTERNAL_ERROR"
    assert "some_internal_key" not in err["message"]
    assert err["hint"]

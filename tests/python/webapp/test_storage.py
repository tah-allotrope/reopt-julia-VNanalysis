"""PHASE-01: filesystem run storage."""

from datetime import datetime, timedelta, timezone

from reopt_pysam_vn.webapp.storage import RunStorage


def test_create_run_writes_deal_config_and_queued_status(storage_root):
    store = RunStorage(storage_root)
    run_id = store.create_run({"case": "TEST", "mode": "onsite", "title": "T"})
    assert (storage_root / run_id / "deal_config.json").exists()
    status = store.get_status(run_id)
    assert status["state"] == "queued"


def test_run_ids_are_unique_and_sortable_by_creation_order():
    from reopt_pysam_vn.webapp.storage import RunStorage
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        store = RunStorage(d)
        id1 = store.create_run({"case": "A", "mode": "onsite"})
        id2 = store.create_run({"case": "B", "mode": "onsite"})
        assert id1 != id2


def test_set_and_get_status_merges_fields(storage_root):
    store = RunStorage(storage_root)
    run_id = store.create_run({"case": "TEST", "mode": "onsite"})
    store.set_status(run_id, state="solving")
    status = store.get_status(run_id)
    assert status["state"] == "solving"
    store.set_status(run_id, state="done", message="ok")
    status = store.get_status(run_id)
    assert status["state"] == "done"
    assert status["message"] == "ok"


def test_save_and_get_result(storage_root):
    store = RunStorage(storage_root)
    run_id = store.create_run({"case": "TEST", "mode": "onsite"})
    store.save_result(run_id, {"case": "TEST", "sizing": {"pv_kw": 100.0}})
    result = store.get_result(run_id)
    assert result["sizing"]["pv_kw"] == 100.0


def test_get_result_returns_none_when_not_solved(storage_root):
    store = RunStorage(storage_root)
    run_id = store.create_run({"case": "TEST", "mode": "onsite"})
    assert store.get_result(run_id) is None


def test_save_and_get_reopt_results(storage_root):
    store = RunStorage(storage_root)
    run_id = store.create_run({"case": "TEST", "mode": "onsite"})
    store.save_reopt_results(run_id, {"PV": {"size_kw": 500.0}})
    assert store.get_reopt_results(run_id)["PV"]["size_kw"] == 500.0


def test_list_runs_sorted_newest_first(storage_root):
    store = RunStorage(storage_root)
    id1 = store.create_run({"case": "A", "mode": "onsite", "title": "First"})
    id2 = store.create_run({"case": "B", "mode": "onsite", "title": "Second"})
    runs = store.list_runs()
    ids = [r["run_id"] for r in runs]
    assert ids[0] == id2
    assert ids[1] == id1


def test_get_deal_config_roundtrips(storage_root):
    store = RunStorage(storage_root)
    cfg = {"case": "TEST", "mode": "offsite_dppa", "title": "hello"}
    run_id = store.create_run(cfg)
    got = store.get_deal_config(run_id)
    assert got["case"] == "TEST"
    assert got["title"] == "hello"


def test_unknown_run_id_raises_key_error(storage_root):
    store = RunStorage(storage_root)
    import pytest

    with pytest.raises(KeyError):
        store.get_status("does-not-exist")


def test_write_and_get_provenance_roundtrips(storage_root):
    store = RunStorage(storage_root)
    run_id = store.create_run({"case": "TEST", "mode": "onsite"})
    prov = {"run_id": run_id, "solver": "nrel_api", "wall_time_seconds": 1.5}
    store.write_provenance(run_id, prov)
    got = store.get_provenance(run_id)
    assert got == prov


def test_get_provenance_returns_none_when_absent(storage_root):
    store = RunStorage(storage_root)
    run_id = store.create_run({"case": "TEST", "mode": "onsite"})
    assert store.get_provenance(run_id) is None


def _backdate_run(storage_root, run_id, days_ago):
    status_path = storage_root / run_id / "status.json"
    import json

    status = json.loads(status_path.read_text(encoding="utf-8"))
    old_ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y%m%dT%H%M%S%f")
    status["created_at"] = old_ts
    status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")


def test_prune_dry_run_selects_but_does_not_delete_stale_done_runs(storage_root):
    store = RunStorage(storage_root)
    old_id = store.create_run({"case": "OLD", "mode": "onsite"})
    store.set_status(old_id, state="done")
    _backdate_run(storage_root, old_id, days_ago=40)

    fresh_id = store.create_run({"case": "FRESH", "mode": "onsite"})
    store.set_status(fresh_id, state="done")

    stale = store.prune(30, dry_run=True)
    assert stale == [old_id]
    assert (storage_root / old_id).exists()
    assert (storage_root / fresh_id).exists()


def test_prune_apply_deletes_only_stale_runs(storage_root):
    store = RunStorage(storage_root)
    old_id = store.create_run({"case": "OLD", "mode": "onsite"})
    store.set_status(old_id, state="done")
    _backdate_run(storage_root, old_id, days_ago=40)

    fresh_id = store.create_run({"case": "FRESH", "mode": "onsite"})
    store.set_status(fresh_id, state="done")

    stale = store.prune(30, dry_run=False)
    assert stale == [old_id]
    assert not (storage_root / old_id).exists()
    assert (storage_root / fresh_id).exists()


def test_prune_never_selects_non_terminal_runs_even_if_old(storage_root):
    store = RunStorage(storage_root)
    run_id = store.create_run({"case": "SOLVING", "mode": "onsite"})
    store.set_status(run_id, state="solving")
    _backdate_run(storage_root, run_id, days_ago=999)

    stale = store.prune(30, dry_run=False)
    assert stale == []
    assert (storage_root / run_id).exists()

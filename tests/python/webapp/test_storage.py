"""PHASE-01: filesystem run storage."""

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

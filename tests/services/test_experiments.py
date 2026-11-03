import json

from backend.services.experiments import load_experiments


def write_run(results_dir, name, started, finished=None, events=()):
    run_dir = results_dir / name
    run_dir.mkdir(parents=True)
    run = {"agents": ["agent-1", "agent-2"], "scenarios": ["delay150"], "repeats": 2, "started_utc": started}
    if finished:
        run["finished_utc"] = finished
    (run_dir / "run.json").write_text(json.dumps(run), encoding="utf-8")
    lines = [json.dumps(event) for event in events]
    (run_dir / "events.jsonl").write_text("\n".join(lines), encoding="utf-8")


def test_load_experiments_reads_run_and_events(tmp_path):
    event = {"ts_utc": "2026-11-03T00:11:38+00:00", "event": "inject_start", "scenario": "delay150", "repeat": 1}
    write_run(tmp_path, "detection_20261103_000000", "2026-11-03T00:00:00+00:00",
              finished="2026-11-03T07:00:00+00:00", events=[event])

    result = load_experiments(tmp_path)

    assert len(result) == 1
    assert result[0]["name"] == "detection_20261103_000000"
    assert result[0]["agents"] == ["agent-1", "agent-2"]
    assert result[0]["finished_utc"] == "2026-11-03T07:00:00+00:00"
    assert result[0]["events"] == [event]


def test_load_experiments_old_single_agent_run(tmp_path):
    run_dir = tmp_path / "detection_old"
    run_dir.mkdir()
    run = {"agent": "agent-2", "scenarios": ["loss2"], "repeats": 8, "started_utc": "2026-11-03T00:00:00+00:00"}
    (run_dir / "run.json").write_text(json.dumps(run), encoding="utf-8")

    assert load_experiments(tmp_path)[0]["agents"] == ["agent-2"]


def test_load_experiments_newest_first(tmp_path):
    write_run(tmp_path, "detection_a", "2026-11-02T23:56:38+00:00")
    write_run(tmp_path, "detection_b", "2026-11-03T21:00:00+00:00")

    names = [e["name"] for e in load_experiments(tmp_path)]

    assert names == ["detection_b", "detection_a"]


def test_load_experiments_running_has_no_finish_time(tmp_path):
    write_run(tmp_path, "detection_a", "2026-11-03T21:00:00+00:00")

    assert load_experiments(tmp_path)[0]["finished_utc"] is None


def test_load_experiments_skips_broken_run_json(tmp_path):
    write_run(tmp_path, "detection_ok", "2026-11-03T21:00:00+00:00")
    broken = tmp_path / "detection_broken"
    broken.mkdir()
    (broken / "run.json").write_text("{not json", encoding="utf-8")

    assert [e["name"] for e in load_experiments(tmp_path)] == ["detection_ok"]


def test_load_experiments_missing_folder_is_empty(tmp_path):
    assert load_experiments(tmp_path / "does-not-exist") == []

import json
from pathlib import Path


def read_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_experiments(results_dir: Path) -> list[dict]:
    experiments = []
    for run_file in results_dir.glob("detection_*/run.json"):
        try:
            run = json.loads(run_file.read_text(encoding="utf-8"))
            experiments.append({
                "name": run_file.parent.name,
                "agents": run.get("agents") or [run["agent"]],
                "started_utc": run["started_utc"],
                "finished_utc": run.get("finished_utc"),
                "scenarios": run["scenarios"],
                "repeats": run["repeats"],
                "events": read_events(run_file.parent / "events.jsonl"),
            })
        except (ValueError, KeyError):
            continue
    return sorted(experiments, key=lambda e: e["started_utc"], reverse=True)

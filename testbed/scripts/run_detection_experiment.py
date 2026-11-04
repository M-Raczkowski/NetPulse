import argparse
import inspect
import json
import random
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "testbed" / "results"

SCENARIOS = {
    "delay20": "delay 20ms",
    "delay150": "delay 150ms",
    "loss2": "loss 2%",
    "loss10": "loss 10%",
    "delay50": "delay 50ms",
    "loss5": "loss 5%",
}
AGENTS = ("agent-1", "agent-2", "agent-3")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compose_exec(service: str, command: list[str], check: bool = True) -> None:
    subprocess.run(["docker", "compose", "exec", "-T", service, *command],
                   cwd=ROOT, check=check, capture_output=True)


def set_netem(service: str, args: str) -> None:
    compose_exec(service, ["tc", "qdisc", "replace", "dev", "eth0", "root", "netem", *args.split()])


def clear_netem(service: str) -> None:
    compose_exec(service, ["tc", "qdisc", "del", "dev", "eth0", "root"], check=False)


LOG_LOCK = threading.Lock() 
FINAL_REST_S = 900


def log_event(path: Path, event: str, **fields) -> None:
    record = {"ts_utc": now_iso(), "event": event, **fields}
    with LOG_LOCK:
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record) + "\n")
        print(record, flush=True)


def git_commit() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return result.stdout.strip()


def detector_config() -> dict:
    try:
        sys.path.insert(0, str(ROOT))
        from backend.anomaly.ewma import ewma
        from backend.anomaly.lifecycle import update_alert
        from backend.anomaly.zscore import z_score
        from backend.services.engine import METRICS_MIN_DEVIATION, METRICS_THRESHOLD
        from backend.services.series import fetch_metric_series

        def defaults(function) -> dict:
            return {name: p.default for name, p in inspect.signature(function).parameters.items()
                    if p.default is not inspect.Parameter.empty}

        return {"thresholds": METRICS_THRESHOLD, "min_deviation": METRICS_MIN_DEVIATION, "zscore": defaults(z_score), "ewma": defaults(ewma),
                "lifecycle": defaults(update_alert), "history_window_min": defaults(fetch_metric_series)["minutes"]}
    except Exception as error:
        return {"error": repr(error)}


def check_stack(base_url: str) -> None:
    since = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    response = httpx.get(f"{base_url}/measurements", params={"since": since, "limit": 500}, timeout=10)
    response.raise_for_status()
    missing = set(AGENTS) - {row["agent_id"] for row in response.json()}
    if missing:
        raise SystemExit(f"no measurements from {sorted(missing)} in the last 60 s; run: docker compose up -d")


def run_agent(stop: threading.Event, events: Path, agent: str, schedule: list[tuple[str, int]],
              start_delay: float, disturb: int, recover: int) -> None:
    try:
        if stop.wait(start_delay):
            return
        for index, (name, repeat) in enumerate(schedule):
            set_netem(agent, SCENARIOS[name])
            log_event(events, "inject_start", scenario=name, netem=SCENARIOS[name], repeat=repeat, agent=agent)
            if stop.wait(disturb):
                return
            clear_netem(agent)
            log_event(events, "inject_end", scenario=name, repeat=repeat, agent=agent)
            rest = min(recover, FINAL_REST_S) if index == len(schedule) - 1 else recover
            if stop.wait(rest):
                return
    except Exception as error:
        log_event(events, "error", agent=agent, message=repr(error))
        stop.set()


def fetch_results(base_url: str, out_dir: Path, since: str, until: str) -> None:
    measurements = httpx.get(f"{base_url}/measurements",
                             params={"since": since, "until": until, "limit": 1_000_000}, timeout=120)
    alerts = httpx.get(f"{base_url}/alerts", params={"limit": 1_000_000}, timeout=120)
    (out_dir / "measurements.json").write_text(json.dumps(measurements.json()), encoding="utf-8")
    (out_dir / "alerts.json").write_text(json.dumps(alerts.json()), encoding="utf-8")


def build_schedules(agents: list[str], scenarios: list[str], repeats: int, rng: random.Random) -> dict:
    schedules = {}
    for agent in agents:
        schedule = []
        for repeat in range(1, repeats + 1):
            round_order = list(scenarios)
            rng.shuffle(round_order)
            schedule += [(name, repeat) for name in round_order]
        schedules[agent] = schedule
    return schedules


def main() -> None:
    parser = argparse.ArgumentParser(description="Detection experiment: inject netem faults on agents, one at a time")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--agents", nargs="+", default=list(AGENTS), choices=list(AGENTS),
                        help="agents that get faults; their faults are staggered and never overlap")
    parser.add_argument("--scenarios", nargs="+", default=list(SCENARIOS), choices=list(SCENARIOS))
    parser.add_argument("--repeats", type=int, default=1, help="how many times each agent runs every scenario")
    parser.add_argument("--baseline", type=int, default=900, help="seconds without faults at the start")
    parser.add_argument("--disturb", type=int, default=300, help="seconds of each fault")
    parser.add_argument("--recover", type=int, default=3700, help="seconds of rest after each fault of one agent")
    parser.add_argument("--stagger", type=int, help="seconds between the first faults of consecutive agents "
                                                    "(default: (disturb + recover) / number of agents)")
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()

    stagger = args.stagger or (args.disturb + args.recover) // len(args.agents)
    if args.disturb >= stagger:
        raise SystemExit(f"--disturb {args.disturb} s is not shorter than the stagger {stagger} s; faults would overlap")
    check_stack(args.base_url)
    detectors = detector_config()
    history_s = detectors.get("history_window_min", 60) * 60
    if args.recover < history_s:
        print(f"warning: --recover {args.recover} s is shorter than the detector history window ({history_s} s); "
              "z-score and EWMA will treat earlier faults as normal behaviour", flush=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = RESULTS_DIR / f"detection_{run_id}"
    out_dir.mkdir(parents=True)
    events = out_dir / "events.jsonl"
    started = now_iso()
    schedules = build_schedules(args.agents, args.scenarios, args.repeats, random.Random(args.seed))
    parameters = {**vars(args), "run_id": run_id, "git_commit": git_commit(), "scenario_netem": SCENARIOS,
                  "stagger": stagger, "schedules": schedules, "detectors": detectors, "started_utc": started}
    (out_dir / "run.json").write_text(json.dumps(parameters, indent=2), encoding="utf-8")

    stop = threading.Event()
    threads = [threading.Thread(target=run_agent, daemon=True,
                                args=(stop, events, agent, schedules[agent], index * stagger, args.disturb, args.recover))
               for index, agent in enumerate(args.agents)]
    completed = False
    try:
        for agent in args.agents:
            clear_netem(agent)
        log_event(events, "baseline_start", seconds=args.baseline)
        time.sleep(args.baseline)
        log_event(events, "baseline_end")
        for thread in threads:
            thread.start()
        while any(thread.is_alive() for thread in threads):
            time.sleep(1)
        completed = not stop.is_set()
    finally:
        stop.set()
        for thread in threads:
            thread.join(timeout=10)
        for agent in args.agents:
            clear_netem(agent)
        finished = now_iso()
        log_event(events, "finished", completed=completed)
        parameters["finished_utc"] = finished
        parameters["completed"] = completed
        (out_dir / "run.json").write_text(json.dumps(parameters, indent=2), encoding="utf-8")
        fetch_results(args.base_url, out_dir, started, finished)
        print(f"results saved in {out_dir}")
        print(f"panel: {args.base_url}/panel/?experiment=detection_{run_id}")


if __name__ == "__main__":
    main()

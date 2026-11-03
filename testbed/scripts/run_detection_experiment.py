import argparse
import json
import random
import subprocess
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


def log_event(path: Path, event: str, **fields) -> None:
    record = {"ts_utc": now_iso(), "event": event, **fields}
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")
    print(record, flush=True)


def git_commit() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return result.stdout.strip()


def check_stack(base_url: str) -> None:
    since = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    response = httpx.get(f"{base_url}/measurements", params={"since": since, "limit": 500}, timeout=10)
    response.raise_for_status()
    missing = set(AGENTS) - {row["agent_id"] for row in response.json()}
    if missing:
        raise SystemExit(f"no measurements from {sorted(missing)} in the last 60 s; run: docker compose up -d")


def run_scenario(events: Path, agent: str, name: str, repeat: int, disturb: int, recover: int) -> None:
    set_netem(agent, SCENARIOS[name])
    log_event(events, "inject_start", scenario=name, netem=SCENARIOS[name], repeat=repeat, agent=agent)
    time.sleep(disturb)
    clear_netem(agent)
    log_event(events, "inject_end", scenario=name, repeat=repeat, agent=agent)
    time.sleep(recover)


def fetch_results(base_url: str, out_dir: Path, since: str, until: str) -> None:
    measurements = httpx.get(f"{base_url}/measurements",
                             params={"since": since, "until": until, "limit": 1_000_000}, timeout=120)
    alerts = httpx.get(f"{base_url}/alerts", params={"limit": 1_000_000}, timeout=120)
    (out_dir / "measurements.json").write_text(json.dumps(measurements.json()), encoding="utf-8")
    (out_dir / "alerts.json").write_text(json.dumps(alerts.json()), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Detection experiment: inject netem faults on one agent")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--agent", default="agent-2", help="agent that gets the faults (others are controls)")
    parser.add_argument("--scenarios", nargs="+", default=list(SCENARIOS), choices=list(SCENARIOS))
    parser.add_argument("--repeats", type=int, default=8)
    parser.add_argument("--baseline", type=int, default=900, help="seconds without faults at the start")
    parser.add_argument("--disturb", type=int, default=300, help="seconds of each fault")
    parser.add_argument("--recover", type=int, default=480, help="seconds of rest after each fault")
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()

    check_stack(args.base_url)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = RESULTS_DIR / f"detection_{run_id}"
    out_dir.mkdir(parents=True)
    events = out_dir / "events.jsonl"
    started = now_iso()
    rng = random.Random(args.seed)
    parameters = {**vars(args), "run_id": run_id, "git_commit": git_commit(), "scenario_netem": SCENARIOS,
                  "started_utc": started}
    (out_dir / "run.json").write_text(json.dumps(parameters, indent=2), encoding="utf-8")

    try:
        clear_netem(args.agent)
        log_event(events, "baseline_start", seconds=args.baseline)
        time.sleep(args.baseline)
        log_event(events, "baseline_end")
        for repeat in range(1, args.repeats + 1):
            order = list(args.scenarios)
            rng.shuffle(order)
            for name in order:
                run_scenario(events, args.agent, name, repeat, args.disturb, args.recover)
    finally:
        clear_netem(args.agent)
        finished = now_iso()
        log_event(events, "finished")
        parameters["finished_utc"] = finished
        (out_dir / "run.json").write_text(json.dumps(parameters, indent=2), encoding="utf-8")
        fetch_results(args.base_url, out_dir, started, finished)
        print(f"results saved in {out_dir}")


if __name__ == "__main__":
    main()

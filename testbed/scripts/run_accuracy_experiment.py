import argparse
import json
import re
import shutil
import socket
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = ROOT / "testbed" / "results"

AGENT_SERVICES = ("agent-1", "agent-2", "agent-3")
WORKER_SERVICE = "agent-1"
TARGET_HOST = "responder"
TARGET_PORT = 9999
IPERF_PORT = 5201
IPERF_PIDFILE = "/tmp/iperf3.pid"
WINDOW_PACKETS = 20
WINDOW_INTERVAL = 0.1
PACKET_TIMEOUT = 1.0
THROUGHPUT_TIMEOUT = 5.0
THROUGHPUT_DURATIONS = (1, 5)
RESULT_PREFIX = "RESULT:"

RTT_CONDITIONS = {
    "none": {"netem": "", "delay_ms": 0, "loss_pct": 0},
    "delay10": {"netem": "delay 10ms", "delay_ms": 10, "loss_pct": 0},
    "delay20": {"netem": "delay 20ms", "delay_ms": 20, "loss_pct": 0},
    "delay50": {"netem": "delay 50ms", "delay_ms": 50, "loss_pct": 0},
    "delay100": {"netem": "delay 100ms", "delay_ms": 100, "loss_pct": 0},
    "loss2": {"netem": "loss 2%", "delay_ms": 0, "loss_pct": 2},
    "loss5": {"netem": "loss 5%", "delay_ms": 0, "loss_pct": 5},
    "loss10": {"netem": "loss 10%", "delay_ms": 0, "loss_pct": 10},
}
THROUGHPUT_CONDITIONS = {
    "unlimited": {"netem": "", "rate_mbit": None},
    "rate100": {"netem": "rate 100mbit", "rate_mbit": 100},
    "rate10": {"netem": "rate 10mbit", "rate_mbit": 10},
    "rate1": {"netem": "rate 1mbit", "rate_mbit": 1},
}
RTT_TOOLS = ("agent", "agent_ip", "ping")
THROUGHPUT_TOOLS = ("agent", "iperf3")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def rotate(items: tuple, shift: int) -> list:
    shift %= len(items)
    return list(items[shift:] + items[:shift])


def set_netem(netem: str) -> None:
    if netem:
        subprocess.run(["tc", "qdisc", "replace", "dev", "eth0", "root", "netem", *netem.split()], check=True)
    else:
        subprocess.run(["tc", "qdisc", "del", "dev", "eth0", "root"], capture_output=True)


def run_agent_rtt(host: str) -> dict:
    from agent.measurements.rtt import measure_rtt
    rtts = measure_rtt(host, TARGET_PORT, count=WINDOW_PACKETS, interval=WINDOW_INTERVAL, timeout=PACKET_TIMEOUT)
    received = [value for value in rtts if value is not None]
    return {"sent": len(rtts), "received": len(received), "rtts": received}


def run_ping(host: str) -> dict:
    result = subprocess.run(["ping", "-c", str(WINDOW_PACKETS), "-i", str(WINDOW_INTERVAL), "-W", str(int(PACKET_TIMEOUT)), host],
                            capture_output=True, text=True)
    rtts = [float(value) for value in re.findall(r"time=([\d.]+) ms", result.stdout)]
    counts = re.search(r"(\d+) packets transmitted, (\d+) (?:packets )?received", result.stdout)
    sent, received = (int(counts.group(1)), int(counts.group(2))) if counts else (WINDOW_PACKETS, len(rtts))
    return {"sent": sent, "received": received, "rtts": rtts}


def run_agent_throughput(duration: float) -> dict:
    from agent.measurements.throughput import measure_throughput
    return {"mbps": measure_throughput(TARGET_HOST, TARGET_PORT, duration, THROUGHPUT_TIMEOUT)}


def run_iperf(duration: int) -> dict:
    result = subprocess.run(["iperf3", "-c", TARGET_HOST, "-p", str(IPERF_PORT), "-t", str(duration), "-J"],
                            capture_output=True, text=True)
    try:
        return {"mbps": json.loads(result.stdout)["end"]["sum_received"]["bits_per_second"] / 1e6}
    except (ValueError, KeyError):
        return {"mbps": None}


def first_line(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True)
    return (result.stdout or result.stderr).splitlines()[0].strip()


def worker(args: argparse.Namespace) -> None:
    missing = [tool for tool in ("ping", "iperf3", "tc") if shutil.which(tool) is None]
    if missing:
        raise SystemExit(f"missing in the agent image: {missing}; run: docker compose build")
    host_ip = socket.gethostbyname(TARGET_HOST)
    rtt_rows, throughput_rows = [], []
    try:
        for name, condition in RTT_CONDITIONS.items():
            set_netem(condition["netem"])
            time.sleep(args.settle)
            log(f"rtt condition {name}: {args.rtt_rounds} rounds")
            for round_index in range(args.rtt_rounds):
                for tool in rotate(RTT_TOOLS, round_index):
                    probe = {"agent": lambda: run_agent_rtt(TARGET_HOST),
                             "agent_ip": lambda: run_agent_rtt(host_ip),
                             "ping": lambda: run_ping(TARGET_HOST)}[tool]
                    rtt_rows.append({"condition": name, "round": round_index, "tool": tool, **probe()})
        for name, condition in THROUGHPUT_CONDITIONS.items():
            set_netem(condition["netem"])
            time.sleep(args.settle)
            log(f"throughput condition {name}: {args.throughput_rounds} rounds")
            for round_index in range(args.throughput_rounds):
                for duration in THROUGHPUT_DURATIONS:
                    for tool in rotate(THROUGHPUT_TOOLS, round_index):
                        value = run_agent_throughput(float(duration)) if tool == "agent" else run_iperf(duration)
                        throughput_rows.append({"condition": name, "round": round_index, "tool": tool,
                                                "duration": duration, **value})
    finally:
        set_netem("")
    versions = {"ping": first_line(["ping", "-V"]), "iperf3": first_line(["iperf3", "--version"]), "target_ip": host_ip}
    print(RESULT_PREFIX + json.dumps({"rtt": rtt_rows, "throughput": throughput_rows, "versions": versions}), flush=True)


def compose(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "compose", *args], cwd=ROOT, **kwargs)


def stop_iperf_server() -> None:
    compose(["exec", "-T", "responder", "sh", "-c", f"kill $(cat {IPERF_PIDFILE}) 2>/dev/null; rm -f {IPERF_PIDFILE}; true"],
            capture_output=True)


def start_iperf_server() -> None:
    stop_iperf_server()
    compose(["exec", "-T", "responder", "iperf3", "-s", "-D", "--pidfile", IPERF_PIDFILE], check=True, capture_output=True)


def git_commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def mean_of(values: list[float]) -> float:
    return statistics.mean(values) if values else float("nan")


def summarize_rtt(rows: list[dict]) -> dict:
    summary = {}
    for row in rows:
        entry = summary.setdefault(row["condition"], {}).setdefault(row["tool"], {"sent": 0, "received": 0, "rtts": []})
        entry["sent"] += row["sent"]
        entry["received"] += row["received"]
        entry["rtts"] += row["rtts"]
    return {condition: {tool: {"sent": e["sent"], "received": e["received"],
                               "loss_pct": 100 * (1 - e["received"] / e["sent"]),
                               "mean_ms": mean_of(e["rtts"]),
                               "median_ms": statistics.median(e["rtts"]) if e["rtts"] else float("nan"),
                               "stdev_ms": statistics.stdev(e["rtts"]) if len(e["rtts"]) > 1 else float("nan")}
                        for tool, e in tools.items()}
            for condition, tools in summary.items()}


def summarize_throughput(rows: list[dict]) -> dict:
    grouped = {}
    for row in rows:
        entry = grouped.setdefault(row["condition"], {}).setdefault(f"{row['tool']}_{row['duration']}s",
                                                                    {"values": [], "failed": 0})
        if row["mbps"] is None:
            entry["failed"] += 1
        else:
            entry["values"].append(row["mbps"])
    return {condition: {key: {"n": len(e["values"]), "failed": e["failed"], "mean_mbps": mean_of(e["values"]),
                              "stdev_mbps": statistics.stdev(e["values"]) if len(e["values"]) > 1 else float("nan")}
                        for key, e in tools.items()}
            for condition, tools in grouped.items()}


def print_summary(rtt: dict, throughput: dict) -> None:
    print("\nRTT and loss (all windows pooled)")
    for condition, tools in rtt.items():
        nominal = RTT_CONDITIONS[condition]
        print(f"\n{condition}  (netem delay {nominal['delay_ms']} ms, loss {nominal['loss_pct']} %)")
        print(f"  {'tool':9} {'loss %':>7} {'mean ms':>9} {'median ms':>10} {'stdev ms':>9} {'received/sent':>14}")
        for tool, s in tools.items():
            print(f"  {tool:9} {s['loss_pct']:7.2f} {s['mean_ms']:9.3f} {s['median_ms']:10.3f} {s['stdev_ms']:9.3f} "
                  f"{s['received']:>7}/{s['sent']:<6}")
        if "ping" in tools:
            for tool in ("agent", "agent_ip"):
                diff = tools[tool]["mean_ms"] - tools["ping"]["mean_ms"]
                print(f"  {tool} - ping: {diff:+.3f} ms ({100 * diff / tools['ping']['mean_ms']:+.1f} %)")
    print("\nThroughput (Mbit/s)")
    for condition, tools in throughput.items():
        print(f"\n{condition}  (netem rate {THROUGHPUT_CONDITIONS[condition]['rate_mbit']} Mbit/s)")
        print(f"  {'tool':12} {'mean':>10} {'stdev':>9} {'ok':>4} {'failed':>7}")
        for key, s in tools.items():
            print(f"  {key:12} {s['mean_mbps']:10.2f} {s['stdev_mbps']:9.2f} {s['n']:4} {s['failed']:7}")
        for duration in THROUGHPUT_DURATIONS:
            agent, iperf = tools.get(f"agent_{duration}s"), tools.get(f"iperf3_{duration}s")
            if agent and iperf and iperf["mean_mbps"] == iperf["mean_mbps"] and agent["mean_mbps"] == agent["mean_mbps"]:
                print(f"  agent / iperf3 at {duration} s: {agent['mean_mbps'] / iperf['mean_mbps']:.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Accuracy experiment: agent measurements vs ping and iperf3 under netem")
    parser.add_argument("--rtt-rounds", type=int, default=40, help="windows of 20 packets per tool and condition")
    parser.add_argument("--throughput-rounds", type=int, default=10, help="runs per tool, duration and condition")
    parser.add_argument("--settle", type=float, default=3.0, help="seconds to wait after changing netem")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        worker(args)
        return

    if compose(["exec", "-T", "responder", "true"], capture_output=True).returncode != 0:
        raise SystemExit("responder is not running; run: docker compose up -d --build")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = RESULTS_DIR / f"accuracy_{run_id}"
    out_dir.mkdir(parents=True)
    started = now_iso()
    parameters = {**{key: value for key, value in vars(args).items() if key != "worker"}, "run_id": run_id,
                  "git_commit": git_commit(), "started_utc": started, "rtt_conditions": RTT_CONDITIONS,
                  "throughput_conditions": THROUGHPUT_CONDITIONS, "window_packets": WINDOW_PACKETS,
                  "window_interval_s": WINDOW_INTERVAL, "throughput_durations_s": THROUGHPUT_DURATIONS}
    (out_dir / "run.json").write_text(json.dumps(parameters, indent=2), encoding="utf-8")

    completed = False
    try:
        log(f"stopping {', '.join(AGENT_SERVICES)} so that they do not disturb the measurements")
        compose(["stop", *AGENT_SERVICES], check=True, capture_output=True)
        start_iperf_server()
        result = compose(["run", "--rm", "-T", "--no-deps", WORKER_SERVICE, "python", "-", "--worker",
                          "--rtt-rounds", str(args.rtt_rounds), "--throughput-rounds", str(args.throughput_rounds),
                          "--settle", str(args.settle)],
                         input=Path(__file__).read_bytes(), stdout=subprocess.PIPE)
        payload = next((line[len(RESULT_PREFIX):] for line in result.stdout.decode("utf-8", "replace").splitlines()
                        if line.startswith(RESULT_PREFIX)), None)
        if payload is None:
            raise SystemExit("worker returned no result; see the messages above")
        data = json.loads(payload)
        completed = True
    finally:
        stop_iperf_server()
        compose(["start", *AGENT_SERVICES], capture_output=True)

    parameters["finished_utc"] = now_iso()
    parameters["completed"] = completed
    parameters["versions"] = data["versions"]
    (out_dir / "run.json").write_text(json.dumps(parameters, indent=2), encoding="utf-8")
    (out_dir / "raw.json").write_text(json.dumps({"rtt": data["rtt"], "throughput": data["throughput"]}), encoding="utf-8")
    rtt, throughput = summarize_rtt(data["rtt"]), summarize_throughput(data["throughput"])
    (out_dir / "summary.json").write_text(json.dumps({"rtt": rtt, "throughput": throughput}, indent=2), encoding="utf-8")
    print_summary(rtt, throughput)
    print(f"\nresults saved in {out_dir}")


if __name__ == "__main__":
    main()

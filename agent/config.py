import os
from dotenv import load_dotenv
from pathlib import Path


def parse_targets(raw: str) -> list[tuple[str, int]]:
    result = []
    for item in raw.split(","):
        host, port = item.strip().rsplit(":", 1)
        result.append((host, int(port)))
    return result


load_dotenv(Path(__file__).parent / ".env")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
AGENT_ID = os.getenv("AGENT_ID", "agent-01")
TARGETS = parse_targets(os.getenv("TARGETS", "127.0.0.1:9999"))
PACKETS_PER_WINDOW = int(os.getenv("PACKETS_PER_WINDOW", "20"))
CYCLE_SECONDS = int(os.getenv("CYCLE_SECONDS", "10"))
PACKET_TIMEOUT = float(os.getenv("PACKET_TIMEOUT", "1.0"))

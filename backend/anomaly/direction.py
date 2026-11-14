def direction_sign(direction: str) -> int:
    if direction == "high":
        return 1
    if direction == "low":
        return -1
    raise ValueError(f"unknown direction: {direction}")

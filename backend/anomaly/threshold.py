def threshold_check(result: float | None, threshold: float) -> bool:
    if result is None or result <= threshold :
        return False
    else:
        return True
import httpx

def send_measurement(base_url: str, payload: dict, timeout: float = 5.0) -> str:
    url = base_url.rstrip("/") + "/measurements"
    try:
        response = httpx.post(url, json=payload, timeout=timeout)
    except httpx.RequestError:
        return "failed"
    if response.status_code == 201:
        return "sent"
    elif response.status_code == 409:
        return "duplicate"
    elif 400 <= response.status_code < 500:
        return "rejected"
    else:
        return "failed"

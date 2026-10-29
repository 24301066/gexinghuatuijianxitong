"""Probe a running desktop instance (used for manual/integration checks)."""

import json
import sys
import urllib.request


def probe(port: int) -> int:
    base = f"http://127.0.0.1:{port}"
    try:
        with urllib.request.urlopen(f"{base}/api/v1/health", timeout=3) as response:
            health = json.loads(response.read().decode("utf-8"))
        print("health:", json.dumps(health, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        print("health failed:", exc)
        return 1

    with urllib.request.urlopen(f"{base}/", timeout=3) as response:
        body = response.read().decode("utf-8")
    print("root:", response.status, "app_div=", '<div id="app">' in body, len(body), "bytes")

    request = urllib.request.Request(
        f"{base}/api/v1/auth/login",
        data=json.dumps({"username": "demo", "password": "demo1234"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        token = json.loads(response.read().decode("utf-8"))["token"]
    print("login: ok, token length", len(token))

    rec_request = urllib.request.Request(
        f"{base}/api/v1/recommendations?size=3",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(rec_request, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    print("recommendations:", [(item["item_id"], item["rank"]) for item in payload["items"]])
    print("model:", payload["model_version"], "degraded:", payload["degraded"])
    return 0


if __name__ == "__main__":
    raise SystemExit(probe(int(sys.argv[1]) if len(sys.argv) > 1 else 8792))

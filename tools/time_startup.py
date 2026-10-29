"""Time how long a freshly started instance takes to answer /api/v1/health."""

import json
import sys
import time
import urllib.request

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8793
url = f"http://127.0.0.1:{port}/api/v1/health"
started = time.monotonic()
while time.monotonic() - started < 60:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            body = json.loads(response.read().decode("utf-8"))
        print(f"ready in {time.monotonic() - started:.1f}s")
        print(json.dumps(body, ensure_ascii=False))
        break
    except Exception:  # noqa: BLE001
        time.sleep(0.5)
else:
    print("not ready within 60s")
    raise SystemExit(1)

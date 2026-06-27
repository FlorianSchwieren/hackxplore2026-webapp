import argparse
import random
import time
from datetime import UTC, datetime

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Jitter mock sensor readings for dashboard demos")
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--secret", default="change-me")
    parser.add_argument("--device-prefix", default="MOCK-")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args()

    while True:
        index = random.randint(1, args.count)
        response = httpx.post(
            f"{args.base_url}/ingest/http",
            json={
                "tree_id": f"{args.device_prefix}{index:05d}",
                "raw_value": random.randint(1900, 2800),
                "rssi": random.randint(-70, -40),
                "created_at": datetime.now(UTC).isoformat(),
            },
            headers={"Authorization": f"Bearer {args.secret}"},
            timeout=10,
        )
        print(response.status_code, response.text)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()

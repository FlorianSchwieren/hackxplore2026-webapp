import argparse
from datetime import UTC, datetime, timedelta

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Post a fake watering reading to /ingest/http")
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--secret", default="change-me")
    parser.add_argument("--tree-id", default="tree_001")
    parser.add_argument("--raw", type=int, default=1900)
    parser.add_argument("--repeat", type=int, default=2)
    args = parser.parse_args()

    started_at = datetime.now(UTC)
    for index in range(args.repeat):
        payload = {
            "tree_id": args.tree_id,
            "raw_value": args.raw,
            "battery_voltage": None,
            "rssi": -47,
            "created_at": (started_at + timedelta(seconds=index * 6)).isoformat(),
        }
        response = httpx.post(
            f"{args.base_url}/ingest/http",
            json=payload,
            headers={"Authorization": f"Bearer {args.secret}"},
            timeout=10,
        )
        response.raise_for_status()
        print(response.json())


if __name__ == "__main__":
    main()

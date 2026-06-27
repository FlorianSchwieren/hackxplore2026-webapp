import argparse
from datetime import UTC, datetime

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset the demo tree to a thirsty reading")
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--secret", default="change-me")
    parser.add_argument("--tree-id", default="tree_001")
    parser.add_argument("--raw", type=int, default=2747)
    args = parser.parse_args()

    response = httpx.post(
        f"{args.base_url}/ingest/http",
        json={
            "tree_id": args.tree_id,
            "raw_value": args.raw,
            "rssi": -47,
            "created_at": datetime.now(UTC).isoformat(),
        },
        headers={"Authorization": f"Bearer {args.secret}"},
        timeout=10,
    )
    response.raise_for_status()
    print(response.json())


if __name__ == "__main__":
    main()

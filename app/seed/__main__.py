import argparse

from app.db import session_context
from app.seed import demo, partnerships, readings, sensors, species, trees, users


def run_all(citywide: bool = False) -> dict[str, int]:
    with session_context() as session:
        return {
            "species": species.seed(session),
            "trees": trees.seed(session, citywide=citywide),
            "sensors": sensors.seed(session),
            "readings": readings.seed(session),
            "users": users.seed(session),
            "partnerships": partnerships.seed(session),
            "demo": demo.seed(session),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Baumpate demo data")
    parser.add_argument(
        "target",
        choices=["all", "species", "trees", "sensors", "readings", "users", "partnerships", "demo"],
    )
    parser.add_argument("--citywide", action="store_true", help="Fetch all Karlsruhe trees from geoportal")
    args = parser.parse_args()

    with session_context() as session:
        if args.target == "all":
            result = run_all(citywide=args.citywide)
        else:
            module = {
                "species": species,
                "trees": trees,
                "sensors": sensors,
                "readings": readings,
                "users": users,
                "partnerships": partnerships,
                "demo": demo,
            }[args.target]
            if args.target == "trees":
                result = {"trees": module.seed(session, citywide=args.citywide)}
            else:
                result = {args.target: module.seed(session)}
    print(result)


if __name__ == "__main__":
    main()

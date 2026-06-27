from app.db import session_context
from app.services.scoring import evaluate_daily, expire_coverage


def run_daily() -> dict[str, int]:
    with session_context() as session:
        expired = expire_coverage(session)
        evaluated = evaluate_daily(session)
        session.commit()
        return {"expired_coverages": expired, "evaluated_partnerships": evaluated}


def main() -> None:
    result = run_daily()
    print(result)


if __name__ == "__main__":
    main()

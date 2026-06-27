from datetime import UTC, date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, text
from sqlmodel import Session, select

from app.calibration import in_healthy_band
from app.config import get_settings
from app.models import Profile, SpeciesWaterProfile, Tree, TreePartnership


def today_berlin() -> date:
    return datetime.now(ZoneInfo("Europe/Berlin")).date()


def daily_streak_next(
    current_streak: int,
    healthy_today: bool | None,
    frozen: bool = False,
    heavy_rain: bool = False,
) -> int:
    if frozen or healthy_today is None or heavy_rain:
        return current_streak
    return current_streak + 1 if healthy_today else 0


def recompute_user_score(session: Session, user_id: UUID) -> int:
    score = session.exec(
        select(func.coalesce(func.sum(TreePartnership.streak), 0)).where(
            TreePartnership.user_id == user_id,
            or_(TreePartnership.active_to.is_(None), TreePartnership.active_to >= today_berlin()),
        )
    ).one()
    profile = session.get(Profile, user_id)
    if profile:
        profile.score = int(score)
        session.add(profile)
    return int(score)


def award_immediate_if_needed(
    session: Session,
    tree_id: UUID,
    transitioned_into_healthy: bool,
    evaluation_date: date | None = None,
) -> bool:
    if not transitioned_into_healthy:
        return False

    evaluation_date = evaluation_date or today_berlin()
    partnership = session.exec(
        select(TreePartnership).where(
            TreePartnership.tree_id == tree_id,
            TreePartnership.role == "owner",
            TreePartnership.active_to.is_(None),
        )
    ).first()
    if not partnership or partnership.last_eval_date == evaluation_date or partnership.streak_frozen:
        return False

    partnership.streak += 1
    partnership.last_eval_date = evaluation_date
    session.add(partnership)
    recompute_user_score(session, partnership.user_id)
    return True


def had_heavy_rain_recently(session: Session) -> bool:
    settings = get_settings()
    result = session.execute(
        text(
            """
            select coalesce(sum(precip_mm), 0) as precip
            from weather_snapshots
            where captured_at >= now() - interval '24 hours'
            """
        )
    ).scalar_one()
    return float(result or 0) > settings.rain_penalty_skip_precip_mm_24h


def evaluate_daily(session: Session, evaluation_date: date | None = None) -> int:
    evaluation_date = evaluation_date or today_berlin()
    heavy_rain = had_heavy_rain_recently(session)
    partnerships = session.exec(
        select(TreePartnership).where(
            or_(TreePartnership.active_to.is_(None), TreePartnership.active_to >= evaluation_date),
            or_(
                TreePartnership.last_eval_date.is_(None),
                TreePartnership.last_eval_date != evaluation_date,
            ),
        )
    ).all()

    changed_users: set[UUID] = set()
    for partnership in partnerships:
        tree = session.get(Tree, partnership.tree_id)
        rain_should_hold = False
        if not tree or tree.moisture_pct is None or not tree.species_profile_id:
            healthy_today = None
        else:
            profile = session.get(SpeciesWaterProfile, tree.species_profile_id)
            if profile is not None:
                moisture = float(tree.moisture_pct)
                healthy_today = in_healthy_band(moisture, profile)
                rain_should_hold = heavy_rain and moisture > float(profile.optimal_max_pct)
            else:
                healthy_today = None
        partnership.streak = daily_streak_next(
            partnership.streak,
            healthy_today,
            frozen=partnership.streak_frozen,
            heavy_rain=rain_should_hold,
        )
        partnership.last_eval_date = evaluation_date
        session.add(partnership)
        changed_users.add(partnership.user_id)

    for user_id in changed_users:
        recompute_user_score(session, user_id)
    return len(partnerships)


def expire_coverage(session: Session, today: date | None = None) -> int:
    today = today or today_berlin()
    rows = session.exec(
        select(TreePartnership).where(
            TreePartnership.role == "caretaker",
            TreePartnership.active_to.is_not(None),
            TreePartnership.active_to < today,
        )
    ).all()
    session.execute(
        text(
            """
            update tree_partnerships tp
            set streak_frozen = false
            where streak_frozen = true
              and exists (
                select 1 from absences a
                where a.partnership_id = tp.id and a.to_date < :today
              )
            """
        ),
        {"today": today},
    )
    session.execute(
        text("update absences set status = 'expired' where status in ('open','covered') and to_date < :today"),
        {"today": today},
    )
    return len(rows)


def generated_at_utc() -> datetime:
    return datetime.now(UTC)

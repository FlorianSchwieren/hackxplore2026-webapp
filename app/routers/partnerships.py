from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import text
from sqlmodel import Session

from app.auth import CurrentUser, require_user
from app.db import get_session
from app.schemas import AdoptRequest, InviteRequest, PartnershipOut, PartnershipResponse
from app.services.scoring import recompute_user_score

router = APIRouter(prefix="/partnerships", tags=["partnerships"])


def _partnership_response(row: dict) -> PartnershipResponse:
    return PartnershipResponse(partnership=PartnershipOut(**row))


@router.post("", response_model=PartnershipResponse, status_code=201)
def adopt_tree(
    payload: AdoptRequest,
    user: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
) -> PartnershipResponse:
    tree = session.execute(
        text("select id, status from trees where id = :tree_id for update"),
        {"tree_id": payload.tree_id},
    ).mappings().first()
    if not tree:
        raise HTTPException(status_code=404, detail="Tree not found")
    if tree["status"] != "available":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tree is already adopted")

    row = session.execute(
        text(
            """
            insert into tree_partnerships (tree_id, user_id, role)
            values (:tree_id, :user_id, 'owner')
            returning id, tree_id, user_id, role, streak, active_from, active_to
            """
        ),
        {"tree_id": payload.tree_id, "user_id": user.id},
    ).mappings().one()
    session.execute(
        text("update trees set status = 'adopted' where id = :tree_id"),
        {"tree_id": payload.tree_id},
    )
    recompute_user_score(session, user.id)
    session.commit()
    return _partnership_response(dict(row))


@router.post("/{partnership_id}/invite", response_model=PartnershipResponse, status_code=201)
def invite_friend(
    partnership_id: UUID,
    payload: InviteRequest,
    user: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
) -> PartnershipResponse:
    owner = session.execute(
        text(
            """
            select tree_id from tree_partnerships
            where id = :id and user_id = :user_id and role = 'owner'
              and (active_to is null or active_to >= current_date)
            """
        ),
        {"id": partnership_id, "user_id": user.id},
    ).mappings().first()
    if not owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can invite")

    invited = session.execute(
        text("select id from profiles where lower(email) = lower(:email)"),
        {"email": payload.email},
    ).mappings().first()
    if not invited:
        raise HTTPException(status_code=404, detail="Invited user profile not found")

    existing = session.execute(
        text(
            """
            select id from tree_partnerships
            where tree_id = :tree_id and user_id = :user_id
              and (active_to is null or active_to >= current_date)
            """
        ),
        {"tree_id": owner["tree_id"], "user_id": invited["id"]},
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a partner")

    row = session.execute(
        text(
            """
            insert into tree_partnerships (tree_id, user_id, role)
            values (:tree_id, :user_id, 'member')
            returning id, tree_id, user_id, role, streak, active_from, active_to
            """
        ),
        {"tree_id": owner["tree_id"], "user_id": invited["id"]},
    ).mappings().one()
    session.commit()
    return _partnership_response(dict(row))


@router.delete("/{partnership_id}", status_code=204)
def leave_partnership(
    partnership_id: UUID,
    user: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
) -> Response:
    row = session.execute(
        text(
            """
            delete from tree_partnerships
            where id = :id and user_id = :user_id
            returning tree_id, user_id
            """
        ),
        {"id": partnership_id, "user_id": user.id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Partnership not found")

    active_count = session.execute(
        text(
            """
            select count(*) from tree_partnerships
            where tree_id = :tree_id and (active_to is null or active_to >= current_date)
            """
        ),
        {"tree_id": row["tree_id"]},
    ).scalar_one()
    if active_count == 0:
        session.execute(
            text("update trees set status = 'available' where id = :tree_id"),
            {"tree_id": row["tree_id"]},
        )
    recompute_user_score(session, row["user_id"])
    session.commit()
    return Response(status_code=204)

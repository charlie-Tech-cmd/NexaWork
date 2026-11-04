import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin_access
from app.api.dependencies_email import get_email_service
from app.db.session import get_db
from app.models.user import User
from app.schemas.employee_registration import (
    PendingEmployeeRegistrationPage,
    RegistrationDecisionResponse,
    RegistrationRejectionRequest,
    RejectedEmployeeRegistrationPage,
)
from app.services.account_lifecycle_service import (
    LifecycleTransitionError,
    decide_registration,
    list_pending_registrations,
    list_rejected_registrations,
)
from app.services.admin_service import get_admin_dashboard_overview
from app.services.email.service import (
    EmailDeliveryUnavailable,
    EmailService,
)
from app.services.email.templates.employee_decision import (
    build_employee_decision_email,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
)


@router.get("/dashboard")
async def admin_dashboard(
    current_admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    return get_admin_dashboard_overview(
        db,
        current_admin.organization_id,
    )


@router.get(
    "/employees/pending",
    response_model=PendingEmployeeRegistrationPage,
)
async def pending_employee_registrations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    if current_admin.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization administrator required",
        )
    return list_pending_registrations(
        db,
        organization_id=current_admin.organization_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/employees/rejected",
    response_model=RejectedEmployeeRegistrationPage,
)
async def rejected_employee_registrations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    if current_admin.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization administrator required",
        )
    return list_rejected_registrations(
        db,
        organization_id=current_admin.organization_id,
        limit=limit,
        offset=offset,
    )


def _decide_employee_registration(
    *,
    user_id: int,
    decision: Literal["approved", "rejected"],
    current_admin: User,
    db: Session,
    email_service: EmailService,
    rejection_reason: str | None = None,
) -> RegistrationDecisionResponse:
    if current_admin.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization administrator required",
        )
    try:
        user = decide_registration(
            db,
            user_id=user_id,
            organization_id=current_admin.organization_id,
            actor_user_id=current_admin.id,
            decision=decision,
            rejection_reason=rejection_reason,
        )
    except LifecycleTransitionError as exc:
        db.rollback()
        if str(exc) == "User not found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registration not found",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    subject, body = build_employee_decision_email(
        full_name=user.full_name,
        decision=decision,
        rejection_reason=rejection_reason,
    )
    notification_status: Literal["sent", "failed"] = "sent"
    try:
        email_service.send(
            recipient=user.email,
            subject=subject,
            body=body,
        )
    except EmailDeliveryUnavailable as exc:
        notification_status = "failed"
        logger.error(
            "Employee registration decision email delivery failed (%s)",
            type(exc).__name__,
        )

    return RegistrationDecisionResponse(
        user_id=user.id,
        approval_status=user.approval_status,
        is_active=user.is_active,
        notification_status=notification_status,
    )


@router.post(
    "/employees/{user_id}/approve",
    response_model=RegistrationDecisionResponse,
)
async def approve_employee_registration(
    user_id: int,
    current_admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
):
    return _decide_employee_registration(
        user_id=user_id,
        decision="approved",
        current_admin=current_admin,
        db=db,
        email_service=email_service,
    )


@router.post(
    "/employees/{user_id}/reject",
    response_model=RegistrationDecisionResponse,
)
async def reject_employee_registration(
    user_id: int,
    payload: RegistrationRejectionRequest | None = None,
    current_admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
):
    return _decide_employee_registration(
        user_id=user_id,
        decision="rejected",
        current_admin=current_admin,
        db=db,
        email_service=email_service,
        rejection_reason=payload.reason if payload else None,
    )

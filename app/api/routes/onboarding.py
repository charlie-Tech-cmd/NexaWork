from urllib.parse import urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_organization,
    require_admin_access,
)
from app.api.dependencies_email import get_email_service
from app.core.config import settings
from app.core.rate_limit import is_organization_onboarding_ip_allowed
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.onboarding import (
    AccountStatusUpdate,
    EmailVerificationRequest,
    EmployeeApprovalAction,
    EmployeeInvitationCreate,
    EmployeeInvitationResponse,
    EmployeeRegistrationRequestCreate,
    EmployeeRegistrationRequestResponse,
    EmployeeAccountResponse,
    InvitationAcceptanceRequest,
    OrganizationRegistrationCodeCreate,
    OrganizationRegistrationCodeResponse,
    OrganizationRegistrationCodeSummary,
    RegistrationStructureRequest,
    RegistrationStructureResponse,
    ResendRegistrationVerificationRequest,
)
from app.services.email.service import EmailService
from app.services.onboarding_service import (
    accept_invitation,
    approve_registration_request,
    create_employee_invitation,
    create_registration_code,
    create_self_registration_request,
    disable_employee_account,
    get_registration_structure,
    list_employee_accounts,
    list_employee_invitations,
    list_registration_codes,
    list_registration_requests,
    reenable_employee_account,
    reject_registration_request,
    resend_registration_verification,
    revoke_registration_code,
    resend_invitation,
    resolve_registration_organization,
    rotate_registration_code,
    revoke_invitation,
    verify_registration_email,
)

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])


def _enforce_onboarding_rate_limit(request: Request, scope: str) -> None:
    client_host = request.client.host if request.client else "unknown"
    key = f"employee-onboarding:{scope}:{client_host}"
    if not is_organization_onboarding_ip_allowed(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many onboarding attempts. Please try again later.",
        )


def _onboarding_link(path: str, token: str) -> str:
    configured_url = urlsplit(settings.password_reset_url)
    if (
        configured_url.scheme.lower() not in {"http", "https"}
        or not configured_url.hostname
        or configured_url.username is not None
        or configured_url.password is not None
    ):
        raise RuntimeError("PASSWORD_RESET_URL must be a valid HTTP(S) URL")
    return urlunsplit(
        (
            configured_url.scheme,
            configured_url.netloc,
            path,
            urlencode({"token": token}),
            "",
        )
    )


@router.post(
    "/registration-codes",
    response_model=OrganizationRegistrationCodeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_org_registration_code(
    payload: OrganizationRegistrationCodeCreate,
    current_admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    try:
        return create_registration_code(
            db,
            current_admin.organization_id,
            current_admin.id,
            payload.expires_in_minutes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not create a unique registration code.",
        ) from exc


@router.get(
    "/registration-codes",
    response_model=list[OrganizationRegistrationCodeSummary],
)
def list_org_registration_codes(
    current_admin: User = Depends(require_admin_access),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    return list_registration_codes(db, current_organization.id)


@router.post(
    "/registration-codes/{code_id}/rotate",
    response_model=OrganizationRegistrationCodeResponse,
    status_code=status.HTTP_201_CREATED,
)
def rotate_org_registration_code(
    code_id: int,
    payload: OrganizationRegistrationCodeCreate,
    current_admin: User = Depends(require_admin_access),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return rotate_registration_code(
            db,
            organization_id=current_organization.id,
            code_id=code_id,
            actor_user_id=current_admin.id,
            expires_in_minutes=payload.expires_in_minutes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not rotate this registration code.",
        ) from exc


@router.post(
    "/registration-codes/{code_id}/revoke",
    response_model=OrganizationRegistrationCodeSummary,
)
def revoke_org_registration_code(
    code_id: int,
    current_admin: User = Depends(require_admin_access),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return revoke_registration_code(
            db,
            organization_id=current_organization.id,
            code_id=code_id,
            actor_user_id=current_admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/registration-structure",
    response_model=RegistrationStructureResponse,
)
def registration_structure(
    payload: RegistrationStructureRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    _enforce_onboarding_rate_limit(http_request, "structure")
    try:
        return {
            "branches": get_registration_structure(db, payload.registration_code),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/register",
    response_model=EmployeeRegistrationRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_employee(
    payload: EmployeeRegistrationRequestCreate,
    http_request: Request,
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
):
    _enforce_onboarding_rate_limit(http_request, "register")
    try:
        organization_id = resolve_registration_organization(db, payload.registration_code)
        request = create_self_registration_request(
            db,
            organization_id=organization_id,
            full_name=payload.full_name,
            email=payload.email,
            password=payload.password,
            job_title=payload.job_title,
            branch_id=payload.branch_id,
            department_id=payload.department_id,
            registration_code=payload.registration_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A matching employee request or account already exists.",
        ) from exc

    email_service.send(
        recipient=request.email,
        subject="Verify your NexaWork employee registration",
        body=(
            "Thank you for registering. Verify your email by opening this link: "
            f"{_onboarding_link('/verify-email', request.verification_token)}"
        ),
    )
    return request


@router.post("/verify-email", response_model=EmployeeRegistrationRequestResponse)
def verify_email(
    payload: EmailVerificationRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    _enforce_onboarding_rate_limit(http_request, "verify")
    try:
        return verify_registration_email(db, payload.token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/resend-verification")
def resend_registration_verification_route(
    payload: ResendRegistrationVerificationRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
):
    _enforce_onboarding_rate_limit(http_request, "resend-verification")
    employee_request = resend_registration_verification(
        db,
        registration_code=payload.registration_code,
        email=payload.email,
    )
    if employee_request is not None:
        if employee_request.verification_token is None:
            raise RuntimeError("Registration verification token was not created")
        email_service.send(
            recipient=employee_request.email,
            subject="Verify your NexaWork employee registration",
            body=(
                "Use this link to verify your email: "
                f"{_onboarding_link('/verify-email', employee_request.verification_token)}"
            ),
        )
    return {
        "message": (
            "If a matching registration request is pending, "
            "a verification link will be sent."
        ),
    }


@router.get(
    "/requests",
    response_model=list[EmployeeRegistrationRequestResponse],
)
def list_requests(
    current_admin: User = Depends(require_admin_access),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    return list_registration_requests(db, current_organization.id)


@router.post(
    "/requests/{request_id}/approve",
    response_model=EmployeeRegistrationRequestResponse,
)
def approve_request(
    request_id: int,
    payload: EmployeeApprovalAction,
    current_admin: User = Depends(require_admin_access),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
):
    try:
        request = approve_registration_request(
            db,
            organization_id=current_organization.id,
            request_id=request_id,
            approved_by_user_id=current_admin.id,
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The employee account could not be created because it conflicts with an existing record.",
        ) from exc

    email_service.send(
        recipient=request.email,
        subject="Your NexaWork registration has been approved",
        body="Your registration was approved and your employee account is ready to use.",
    )
    return request


@router.post(
    "/requests/{request_id}/reject",
    response_model=EmployeeRegistrationRequestResponse,
)
def reject_request(
    request_id: int,
    payload: EmployeeApprovalAction,
    current_admin: User = Depends(require_admin_access),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
):
    try:
        request = reject_registration_request(
            db,
            organization_id=current_organization.id,
            request_id=request_id,
            rejected_by_user_id=current_admin.id,
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    email_service.send(
        recipient=request.email,
        subject="Your NexaWork registration was not approved",
        body=(
            "Your registration request was reviewed and not approved. "
            f"Reason: {request.approval_reason or 'No reason provided'}"
        ),
    )
    return request


@router.post(
    "/invitations",
    response_model=EmployeeInvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_invitation(
    payload: EmployeeInvitationCreate,
    current_admin: User = Depends(require_admin_access),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
):
    try:
        invitation = create_employee_invitation(
            db,
            organization_id=current_organization.id,
            created_by_user_id=current_admin.id,
            full_name=payload.full_name,
            email=payload.email,
            job_title=payload.job_title,
            branch_id=payload.branch_id,
            department_id=payload.department_id,
            expires_in_minutes=payload.expires_in_minutes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An invitation or account already exists for this email.",
        ) from exc

    email_service.send(
        recipient=invitation.email,
        subject="Your NexaWork employee invitation",
        body=(
            "You have been invited to join NexaWork. Accept your invitation here: "
            f"{_onboarding_link('/accept-invitation', invitation.invitation_token)}"
        ),
    )
    return invitation


@router.get("/invitations", response_model=list[EmployeeInvitationResponse])
def list_invitations(
    current_admin: User = Depends(require_admin_access),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    return list_employee_invitations(db, current_organization.id)


@router.get(
    "/employees",
    response_model=list[EmployeeAccountResponse],
)
def list_employees(
    current_admin: User = Depends(require_admin_access),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    return list_employee_accounts(db, current_organization.id)


@router.post("/invitations/{invitation_id}/resend", response_model=EmployeeInvitationResponse)
def resend_invitation_route(
    invitation_id: int,
    current_admin: User = Depends(require_admin_access),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
):
    try:
        invitation = resend_invitation(
            db,
            invitation_id,
            current_organization.id,
            current_admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    email_service.send(
        recipient=invitation.email,
        subject="Your NexaWork invitation has been resent",
        body=(
            "Your invitation has been resent. Accept it here: "
            f"{_onboarding_link('/accept-invitation', invitation.invitation_token)}"
        ),
    )
    return invitation


@router.post("/invitations/{invitation_id}/revoke", response_model=EmployeeInvitationResponse)
def revoke_invitation_route(
    invitation_id: int,
    current_admin: User = Depends(require_admin_access),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return revoke_invitation(
            db,
            invitation_id,
            current_organization.id,
            current_admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/invitations/accept", response_model=EmployeeInvitationResponse)
def accept_invitation_route(
    payload: InvitationAcceptanceRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    _enforce_onboarding_rate_limit(http_request, "accept-invitation")
    try:
        return accept_invitation(db, token=payload.token, password=payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This invitation could not be accepted because an account already exists.",
        ) from exc


@router.post("/employees/{employee_id}/disable", response_model=EmployeeRegistrationRequestResponse)
def disable_employee(
    employee_id: int,
    payload: AccountStatusUpdate,
    current_user: User = Depends(require_admin_access),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
):
    try:
        employee = disable_employee_account(
            db,
            employee_id,
            current_organization.id,
            current_user.id,
            payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user = db.scalar(
        select(User).where(User.id == employee.user_id, User.organization_id == current_organization.id)
    )
    email = user.email if user is not None else current_user.email
    full_name = user.full_name if user is not None else current_user.full_name

    email_service.send(
        recipient=email,
        subject="Employee account disabled",
        body=(
            f"Employee account #{employee_id} was disabled. "
            f"Reason: {payload.reason or 'No reason provided'}"
        ),
    )
    return EmployeeRegistrationRequestResponse(
        id=employee.id,
        organization_id=employee.organization_id,
        email=email,
        full_name=full_name,
        branch_id=employee.branch_id,
        department_id=employee.department_id,
        job_title=employee.job_title,
        email_verification_status=employee.email_verification_status,
        approval_status=employee.approval_status,
        account_status=employee.account_status,
        approval_reason=employee.approval_reason,
        created_at=employee.created_at,
    )


@router.post("/employees/{employee_id}/enable", response_model=EmployeeRegistrationRequestResponse)
def enable_employee(
    employee_id: int,
    current_user: User = Depends(require_admin_access),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        employee = reenable_employee_account(
            db,
            employee_id,
            current_organization.id,
            current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user = db.scalar(
        select(User).where(User.id == employee.user_id, User.organization_id == current_organization.id)
    )
    email = user.email if user is not None else current_user.email
    full_name = user.full_name if user is not None else current_user.full_name

    return EmployeeRegistrationRequestResponse(
        id=employee.id,
        organization_id=employee.organization_id,
        email=email,
        full_name=full_name,
        branch_id=employee.branch_id,
        department_id=employee.department_id,
        job_title=employee.job_title,
        email_verification_status=employee.email_verification_status,
        approval_status=employee.approval_status,
        account_status=employee.account_status,
        approval_reason=employee.approval_reason,
        created_at=employee.created_at,
    )

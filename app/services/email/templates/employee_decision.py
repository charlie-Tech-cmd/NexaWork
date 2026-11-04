from typing import Literal


RegistrationDecision = Literal["approved", "rejected"]


def build_employee_decision_email(
    *,
    full_name: str,
    decision: RegistrationDecision,
    rejection_reason: str | None = None,
) -> tuple[str, str]:
    if decision == "approved":
        subject = "Your NexaWork registration was approved"
        message = (
            "Your employee registration has been approved. "
            "You can now sign in to your NexaWork workspace."
        )
    else:
        subject = "Your NexaWork registration update"
        message = "Your employee registration was not approved."
        if rejection_reason:
            message += f"\n\nReason: {rejection_reason}"

    body = f"Hello {full_name},\n\n{message}\n\nNexaWork"
    return subject, body

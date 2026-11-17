"""
RIT-Sync Vision - Capture Session Guard
Author: Paul Bryton Raj (AI & System Lead)

AI-side enforcement of "no valid authorization -> no capture" (PRD FR-001, plan Phase I.6-7).

Responsibility split:
- The backend (Vijayalakshmi) issues, signs and stores capture permits and authenticates teachers.
- The AI engine refuses to open the camera unless the session context carries a permit that is
  present, unexpired and (when a verifier is supplied by the backend) cryptographically valid.

Note: a valid permit proves the capture was authorized. It does NOT prove that frames came from a
genuine live camera, nor that a student was physically present.
"""

from datetime import datetime, timezone
from typing import Callable, List, Optional, Tuple
from shared.constants import ReasonCode
from shared.schemas import SessionContext

PermitVerifier = Callable[[SessionContext], bool]


def _parse_iso(ts: str) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class SessionGuard:
    def __init__(self, permit_verifier: Optional[PermitVerifier] = None, require_expiry: bool = False):
        """
        :param permit_verifier: Backend-provided callable that verifies the permit signature/state.
        :param require_expiry: If True, a permit without `permit_expires_at` is rejected.
        """
        self.permit_verifier = permit_verifier
        self.require_expiry = require_expiry

    def validate(
        self, ctx: SessionContext, now: Optional[datetime] = None
    ) -> Tuple[bool, List[ReasonCode]]:
        """
        :return: (is_authorized, reason_codes). Capture must not start when is_authorized is False.
        """
        now = now or datetime.now(timezone.utc)

        if not ctx.permit_id or not ctx.permit_id.strip():
            return False, [ReasonCode.PERMIT_INVALID]
        if not ctx.teacher_id or not ctx.session_id:
            return False, [ReasonCode.PERMIT_INVALID]

        if ctx.permit_expires_at:
            expiry = _parse_iso(ctx.permit_expires_at)
            if expiry is None:
                return False, [ReasonCode.PERMIT_INVALID]
            if now >= expiry:
                return False, [ReasonCode.PERMIT_EXPIRED]
        elif self.require_expiry:
            return False, [ReasonCode.PERMIT_INVALID]

        if self.permit_verifier is not None:
            try:
                if not self.permit_verifier(ctx):
                    return False, [ReasonCode.PERMIT_INVALID]
            except Exception:
                return False, [ReasonCode.PERMIT_INVALID]

        return True, []

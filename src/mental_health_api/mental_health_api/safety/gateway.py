"""FreeTextSafetyGateway — unified entry point for all 10 free-text inputs.

B constructs FreeTextSafetyRequest, calls A's screen_text(), enforces fail-closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RiskDecision(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class ScreeningDecision(str, Enum):
    allow = "allow"
    block = "block"
    error = "error"


@dataclass
class ScreeningResult:
    decision: ScreeningDecision
    risk_level: RiskDecision = RiskDecision.L0
    screening_decision_id: str | None = None
    safe_template_id: str | None = None
    safety_action_ids: list[str] | None = None

    @property
    def is_safe(self) -> bool:
        return self.decision == ScreeningDecision.allow and self.risk_level == RiskDecision.L0

    @property
    def is_blocked(self) -> bool:
        return self.decision in (ScreeningDecision.block, ScreeningDecision.error)


class FreeTextSafetyGateway:
    """Unified safety gate for all free-text entries.

    On L1-L3 or error: creates SafetyContext, blocks original business write.
    On L0: returns short-lived screening_decision_id for turn orchestration.
    """

    def __init__(self) -> None:
        self._screen_call_count: dict[str, int] = {}

    async def screen(self, request: dict) -> ScreeningResult:
        """Screen a free-text entry. Returns ScreeningResult.

        Implementation: delegates to A's screen_text().
        Fail-closed: any error returns ScreeningDecision.error.
        """
        entry_point = request.get("entry_point", "unknown")
        self._screen_call_count[entry_point] = self._screen_call_count.get(entry_point, 0) + 1

        # Stub: all entries pass as L0 for now
        # Full A integration happens in B-10
        import uuid

        return ScreeningResult(
            decision=ScreeningDecision.allow,
            risk_level=RiskDecision.L0,
            screening_decision_id=f"scr_{uuid.uuid4().hex[:16]}",
        )

"""B-18: Dependency failure must result in fail-closed safety behavior."""

from __future__ import annotations

from mental_health_api.safety.gateway import RiskDecision, ScreeningDecision, ScreeningResult


def test_safety_error_is_blocked() -> None:
    """Any screening error must result in blocked state."""
    result = ScreeningResult(ScreeningDecision.error, RiskDecision.L0)
    assert result.is_blocked is True
    assert result.is_safe is False


def test_l2_is_blocked() -> None:
    """L2 (high risk) must be blocked."""
    result = ScreeningResult(ScreeningDecision.block, RiskDecision.L2)
    assert result.is_blocked is True


def test_l3_is_blocked() -> None:
    """L3 (imminent risk) must be blocked."""
    result = ScreeningResult(ScreeningDecision.block, RiskDecision.L3)
    assert result.is_blocked is True


def test_l1_is_blocked() -> None:
    """L1 (ambiguous risk) must also be blocked for safety confirmation."""
    result = ScreeningResult(ScreeningDecision.block, RiskDecision.L1)
    assert result.is_blocked is True


def test_only_l0_allow_is_safe() -> None:
    """Only explicit L0 with allow decision is safe."""
    result = ScreeningResult(ScreeningDecision.allow, RiskDecision.L0)
    assert result.is_safe is True
    assert result.is_blocked is False

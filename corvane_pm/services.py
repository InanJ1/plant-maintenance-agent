"""Corvane-specific workflow services, registered on machina's WorkflowEngine.

Each public method is a workflow action (``corvane.<method>``). The heavy
lifting stays in machina: ``diagnose`` ranks failure modes with machina's own
``FailureAnalyzer`` and returns machina's ``DiagnosisResult``; drafts are built
by machina's ``WorkOrderFactory``. What this module adds is Corvane's policy:

- diagnosis scoped to the failure modes that apply to the alarming asset,
  with related out-of-limit readings counted as extra symptoms and ties broken
  by how often each failure mode appears in the machine model's history
- a repair-kit lookup (failure mode + machine model -> parts, skills, hours)
  checked against the local storeroom's stock
- the planners' priority policy (criticality x severity, trip-limit and
  repeat-failure escalation)
- a human approval step before anything is sent to the CMMS
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from machina.domain.alarm import Alarm, Severity
from machina.domain.services.failure_analyzer import DiagnosisResult, FailureAnalyzer
from machina.domain.work_order import FailureImpact, SparePartRequirement, WorkOrder

if TYPE_CHECKING:
    from machina.domain.asset import Asset
    from machina.domain.failure_mode import FailureMode
    from machina.domain.spare_part import SparePart

    from corvane_pm.approvals import Approver


def _confidence(overlap: int, n_indicators: int) -> str:
    """Same categorical thresholds machina's FailureAnalyzer uses (0.5 / 0.2)."""
    ratio = overlap / n_indicators if n_indicators else 0.0
    if ratio >= 0.5:
        return "high"
    if ratio >= 0.2:
        return "medium"
    return "low"


class CorvaneServices:
    """Workflow actions for Corvane's alarm-to-work-order process."""

    def __init__(
        self,
        *,
        assets: dict[str, Asset],
        failure_modes: list[FailureMode],
        history: list[WorkOrder],
        repair_kits: dict[str, Any],
        alarm_parameters: dict[str, Any],
        policy: dict[str, Any],
        approver: Approver,
    ) -> None:
        self._assets = assets
        self._catalog = {fm.code: fm for fm in failure_modes}
        self._kits = repair_kits
        self._params = alarm_parameters
        self._policy = policy
        self._approver = approver
        # Corrective history counts per (machine model, failure mode), used to
        # order candidates so the most common cause wins a tie.
        self._frequency: Counter[tuple[str, str]] = Counter()
        for wo in history:
            asset = assets.get(wo.asset_id)
            if asset and wo.failure_mode and wo.type.value == "corrective":
                self._frequency[(asset.model, wo.failure_mode)] += 1

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def asset(self, asset_id: str) -> Asset:
        try:
            return self._assets[asset_id]
        except KeyError:
            raise ValueError(f"unknown asset {asset_id!r}") from None

    def out_of_limit(self, parameter: str, value: float, limit: str = "warn") -> bool:
        """Whether ``value`` is past the parameter's warn (or trip) limit."""
        spec = self._params.get(parameter)
        if spec is None:
            return False
        bound = float(spec[limit])
        return value > bound if spec["direction"] == "high" else value < bound

    # ------------------------------------------------------------------
    # workflow actions
    # ------------------------------------------------------------------

    def diagnose(
        self,
        *,
        asset_id: str,
        parameter: str,
        value: float,
        related_readings: dict[str, float] | None = None,
        **_: Any,
    ) -> DiagnosisResult:
        """Rank the asset's failure modes for this alarm with machina's FailureAnalyzer."""
        asset = self.asset(asset_id)
        scoped = [self._catalog[c] for c in asset.failure_modes if c in self._catalog]
        # Stable sort: most frequent in this model's history first. machina's
        # analyzer sorts by indicator overlap (stable), so this order breaks ties.
        scoped.sort(key=lambda fm: -self._frequency[(asset.model, fm.code)])

        signals = {parameter}
        for name, reading in (related_readings or {}).items():
            if self.out_of_limit(name, float(reading)):
                signals.add(name)
        alarms = [
            Alarm(id=f"sig-{name}", asset_id=asset_id, severity=Severity.WARNING,
                  parameter=name, value=float(value if name == parameter else related_readings[name]),
                  threshold=0.0)
            for name in sorted(signals)
        ]
        ranked = FailureAnalyzer(failure_modes=scoped).diagnose(alarms=alarms)
        matches = []
        for fm in ranked:
            hits = sorted(signals & set(fm.typical_indicators))
            matches.append({
                "code": fm.code,
                "name": fm.name,
                "iso_14224_code": fm.iso_14224_code or "",
                "category": fm.category,
                "mechanism": fm.mechanism,
                "matching_indicators": hits,
                "recommended_actions": fm.recommended_actions,
                "confidence": _confidence(len(hits), len(fm.typical_indicators)),
                "history_count": self._frequency[(asset.model, fm.code)],
            })
        return DiagnosisResult(matches=matches)

    def plan_parts(
        self,
        *,
        asset_id: str,
        failure_mode: str | None,
        stock: list[SparePart] | None,
        **_: Any,
    ) -> dict[str, Any]:
        """Look up the repair kit and check it against the local storeroom."""
        asset = self.asset(asset_id)
        if not failure_mode:
            return {"failure_mode": None, "parts": [], "skills": [], "hours": None,
                    "shortfalls": [], "parts_hold": False,
                    "note": "no confident diagnosis, parts not planned"}
        kit = self._kits.get(failure_mode, {})
        hold_days = int(self._policy["parts_hold_lead_time_days"])
        by_sku: dict[str, list[SparePart]] = {}
        for part in stock or []:
            by_sku.setdefault(part.sku, []).append(part)
        planned = []
        for line in (kit.get("parts") or {}).get(asset.model, []):
            records = by_sku.get(line["sku"], [])
            on_hand = sum(p.stock_quantity for p in records)
            shortfall = max(0, int(line["qty"]) - on_hand)
            planned.append({
                "sku": line["sku"],
                "qty": int(line["qty"]),
                "name": records[0].name if records else "",
                "on_hand": on_hand,
                "shortfall": shortfall,
                "lead_time_days": records[0].lead_time_days if records else None,
                "location": records[0].warehouse_location if records else "not stocked at site",
            })
        shortfalls = [p for p in planned if p["shortfall"] > 0]
        return {
            "failure_mode": failure_mode,
            "parts": planned,
            "skills": list(kit.get("skills", [])),
            "hours": kit.get("hours"),
            "shortfalls": shortfalls,
            "parts_hold": any((p["lead_time_days"] or 0) > hold_days for p in shortfalls),
        }

    def assess_priority(
        self,
        *,
        asset_id: str,
        severity: str,
        parameter: str,
        value: float,
        failure_mode: str | None,
        history: list[WorkOrder] | None,
        alarm_time: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        """Apply Corvane's priority policy (config/priority_policy.yaml)."""
        asset = self.asset(asset_id)
        crit = asset.criticality.value
        reasons = []
        effective = "critical" if severity == "critical" else "warning"
        if effective == "warning" and self.out_of_limit(parameter, float(value), "trip"):
            effective = "critical"
            reasons.append(f"{parameter}={value} is past the trip limit")
        level = self._policy["base"][crit][effective]
        reasons.insert(0, f"criticality {crit} + {effective} -> {level}")

        repeat_of = None
        if failure_mode and history:
            when = _parse_time(alarm_time)
            window = timedelta(days=int(self._policy["repeat_window_days"]))
            for wo in history:
                if wo.failure_mode == failure_mode and when - window <= wo.updated_at <= when:
                    repeat_of = wo.id
                    break
        if repeat_of:
            levels = self._policy["levels"]
            raised = levels[min(levels.index(level) + 1, len(levels) - 1)]
            reasons.append(f"repeat of {repeat_of} within {self._policy['repeat_window_days']} days -> {raised}")
            level = raised
        return {"priority": level, "effective_severity": effective,
                "repeat_of": repeat_of, "reasons": reasons}

    def complete_draft(
        self,
        *,
        work_order: WorkOrder,
        parts_plan: dict[str, Any] | None,
        priority: dict[str, Any],
        diagnosis: DiagnosisResult,
        alarm: dict[str, Any],
        **_: Any,
    ) -> WorkOrder:
        """Fill in parts, skills, hours and audit metadata on the factory's draft."""
        plan = parts_plan or {"parts": [], "skills": [], "hours": None, "shortfalls": []}
        draft = work_order.model_copy(deep=True)
        draft.spare_parts = [SparePartRequirement(sku=p["sku"], qty=p["qty"]) for p in plan["parts"]]
        draft.requested_skills = list(plan.get("skills") or [])
        draft.estimated_duration_hours = plan.get("hours")
        draft.failure_impact = (
            FailureImpact.CRITICAL if priority["effective_severity"] == "critical"
            else FailureImpact.INCIPIENT
        )
        draft.metadata = {
            "source": "corvane-alarm-workflow",
            "alarm_id": alarm.get("alarm_id"),
            "alarm": f"{alarm.get('parameter')}={alarm.get('value')} (limit {alarm.get('threshold')})",
            "diagnosis": str(diagnosis),
            "priority_reasons": priority["reasons"],
            "parts_shortfalls": [f"{p['sku']} short {p['shortfall']} (lead {p['lead_time_days']} d)"
                                 for p in plan.get("shortfalls", [])],
            "parts_hold": plan.get("parts_hold", False),
            "requires_approval": True,
        }
        return draft

    async def request_approval(self, *, work_order: WorkOrder, **_: Any) -> dict[str, Any]:
        """Ask a planner to approve the draft. Nothing reaches the CMMS without a yes."""
        decision = await self._approver(work_order)
        return {"approved": decision.approved, "approver": decision.approver,
                "note": decision.note, "mode": decision.mode}


def _parse_time(text: str | None) -> datetime:
    if not text:
        return datetime.now(UTC)
    when = datetime.fromisoformat(str(text))
    return when if when.tzinfo else when.replace(tzinfo=UTC)

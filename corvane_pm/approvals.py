"""Human approval for drafted work orders.

machina's ``Agent.trigger_workflow`` path is guarded only by sandbox mode (its
confirmation gate covers LLM tool calls, not workflows). Corvane's rule is that
no work order reaches the CMMS without a planner's yes, so the workflow has an
explicit approval step and the submit step is guarded on its result.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass

from machina.domain.work_order import WorkOrder


@dataclass(frozen=True)
class Decision:
    approved: bool
    approver: str
    note: str
    mode: str  # "console", "scripted" or "none"


Approver = Callable[[WorkOrder], Awaitable[Decision]]


def render_draft(wo: WorkOrder) -> str:
    """Short planner-facing summary of a drafted work order."""
    meta = wo.metadata
    parts = ", ".join(f"{p.sku} x{p.qty}" for p in wo.spare_parts) or "none"
    lines = [
        f"Draft {wo.id} for {wo.asset_id}  [{wo.type.value}, priority {wo.priority.value}]",
        f"  Alarm:          {meta.get('alarm_id')}  {meta.get('alarm')}",
        f"  Failure mode:   {wo.failure_mode or 'not set (no confident diagnosis)'}",
        f"  Diagnosis:      {meta.get('diagnosis')}",
        f"  Priority why:   {'; '.join(meta.get('priority_reasons', []))}",
        f"  Parts:          {parts}",
        f"  Skills / hours: {', '.join(wo.requested_skills) or '-'} / {wo.estimated_duration_hours}",
    ]
    if meta.get("parts_shortfalls"):
        hold = " (PARTS HOLD)" if meta.get("parts_hold") else ""
        lines.append(f"  Shortfalls:     {'; '.join(meta['parts_shortfalls'])}{hold}")
    return "\n".join(lines)


def console_approver(approver_id: str = "planner") -> Approver:
    """Ask on the terminal. Anything other than 'y' or 'yes' is a no."""

    async def ask(wo: WorkOrder) -> Decision:
        print(render_draft(wo))
        answer = await asyncio.to_thread(input, "  Approve and submit to the CMMS? [y/N] ")
        approved = answer.strip().lower() in {"y", "yes"}
        return Decision(approved, approver_id, f"answered {answer.strip()!r}", "console")

    return ask


def scripted_approver(answers: Iterable[bool], approver_id: str = "scripted-planner") -> Approver:
    """Pre-set answers, for demos and tests. Marked as scripted in the output."""
    queue = list(answers)

    async def ask(wo: WorkOrder) -> Decision:
        approved = queue.pop(0) if queue else False
        return Decision(approved, approver_id, "pre-set answer", "scripted")

    return ask


def no_approver() -> Approver:
    """No human in the loop (evaluation runs): every draft stays a draft."""

    async def ask(wo: WorkOrder) -> Decision:
        return Decision(False, "", "no approver in this run; draft not submitted", "none")

    return ask

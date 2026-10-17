"""Corvane's alarm-to-work-order workflow on machina's workflow engine.

Steps (all deterministic, no LLM call):

1. diagnose           corvane.diagnose (machina FailureAnalyzer, scoped to the asset)
2. check_history      cmms.read_maintenance_history   (machina GenericCmmsConnector)
3. check_spare_parts  cmms.read_spare_parts           (machina GenericCmmsConnector)
4. plan_parts         corvane.plan_parts (repair kit vs local stock)
5. assess_priority    corvane.assess_priority (planner policy)
6. draft_work_order   work_order_factory.create       (machina WorkOrderFactory)
7. complete_draft     corvane.complete_draft (parts, skills, hours, audit metadata)
8. request_approval   corvane.request_approval (human yes/no)
9. submit_work_order  cmms.create_work_order  [write, guarded on approval, sandboxed]
10. notify_technician channels.send_message   [write, guarded on approval, sandboxed]

Every step sets ``is_write`` explicitly: machina's write heuristic matches
substrings such as "set" and "complete", which would wrongly gate
``assess_priority`` or ``complete_draft`` in sandbox mode.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from machina.connectors.base import ConnectorRegistry, set_sandbox_mode
from machina.connectors.cmms import GenericCmmsConnector
from machina.connectors.comms.cli import CliChannel
from machina.domain.services.work_order_factory import WorkOrderFactory
from machina.observability.tracing import ActionTracer
from machina.workflows import (
    ErrorPolicy,
    GuardCondition,
    Step,
    Trigger,
    TriggerType,
    Workflow,
    WorkflowEngine,
)

from corvane_pm.services import CorvaneServices

if TYPE_CHECKING:
    from machina.workflows.models import WorkflowResult

    from corvane_pm.approvals import Approver


def _approved(ctx: dict[str, Any]) -> bool:
    decision = ctx.get("request_approval") or {}
    return bool(decision.get("approved"))


APPROVAL_GUARD = GuardCondition(check=_approved, description="Only approved drafts leave the workflow")

_ASSET = "{trigger.asset_id}"

corvane_alarm_to_workorder = Workflow(
    name="Corvane Alarm to Work Order",
    description="Diagnose a condition-monitoring alarm, plan parts, set priority, "
    "draft a work order and hold it for planner approval.",
    trigger=Trigger(type=TriggerType.ALARM, filter={"severity": ["warning", "critical"]}),
    steps=[
        Step("diagnose", action="corvane.diagnose", is_write=False,
             description="Rank the asset's failure modes for the alarm",
             inputs={"asset_id": _ASSET, "parameter": "{trigger.parameter}",
                     "value": "{trigger.value}", "related_readings": "{trigger.related_readings}"},
             on_error=ErrorPolicy.STOP),
        Step("check_history", action="cmms.read_maintenance_history", is_write=False,
             inputs={"asset_id": _ASSET}, on_error=ErrorPolicy.SKIP),
        Step("check_spare_parts", action="cmms.read_spare_parts", is_write=False,
             inputs={"asset_id": _ASSET}, on_error=ErrorPolicy.SKIP),
        Step("plan_parts", action="corvane.plan_parts", is_write=False,
             inputs={"asset_id": _ASSET, "failure_mode": "{diagnose.failure_mode_for_write}",
                     "stock": "{check_spare_parts}"},
             on_error=ErrorPolicy.STOP),
        Step("assess_priority", action="corvane.assess_priority", is_write=False,
             inputs={"asset_id": _ASSET, "severity": "{trigger.severity}",
                     "parameter": "{trigger.parameter}", "value": "{trigger.value}",
                     "failure_mode": "{diagnose.failure_mode_for_write}",
                     "history": "{check_history}", "alarm_time": "{trigger.timestamp}"},
             on_error=ErrorPolicy.STOP),
        Step("draft_work_order", action="work_order_factory.create", is_write=False,
             inputs={"asset_id": _ASSET, "priority": "{assess_priority.priority}",
                     "failure_mode": "{diagnose.failure_mode_for_write}",
                     "description": "Alarm {trigger.alarm_id}: {trigger.parameter} = "
                                    "{trigger.value} (limit {trigger.threshold}). "
                                    "Diagnosis: {diagnose}"},
             on_error=ErrorPolicy.STOP),
        Step("complete_draft", action="corvane.complete_draft", is_write=False,
             inputs={"work_order": "{draft_work_order}", "parts_plan": "{plan_parts}",
                     "priority": "{assess_priority}", "diagnosis": "{diagnose}",
                     "alarm": "{trigger}"},
             on_error=ErrorPolicy.STOP),
        Step("request_approval", action="corvane.request_approval", is_write=False,
             inputs={"work_order": "{complete_draft}"}, on_error=ErrorPolicy.STOP),
        Step("submit_work_order", action="cmms.create_work_order", is_write=True,
             guard=APPROVAL_GUARD, inputs={"work_order": "{complete_draft}"},
             on_error=ErrorPolicy.STOP),
        Step("notify_technician", action="channels.send_message", is_write=True,
             guard=APPROVAL_GUARD,
             template="New work order for {trigger.asset_id} ({assess_priority.priority}): "
                      "{diagnose.primary_code}. Parts: {plan_parts.parts}",
             on_error=ErrorPolicy.NOTIFY),
    ],
)


@dataclass
class CorvaneRuntime:
    """Connected CMMS connector, services and engine for one run."""

    cmms: GenericCmmsConnector
    services: CorvaneServices
    engine: WorkflowEngine
    tracer: ActionTracer
    sandbox: bool

    async def run_alarm(self, alarm: dict[str, Any]) -> WorkflowResult:
        """Run the workflow for one alarm event (dict as in eval/alarms.yaml)."""
        workflow = corvane_alarm_to_workorder
        assert isinstance(workflow.trigger, Trigger)
        if not workflow.trigger.matches(alarm):
            raise ValueError(f"alarm {alarm.get('alarm_id')} does not match the workflow trigger")
        event = {"related_readings": {}, "timestamp": None, **alarm}
        return await self.engine.execute(workflow, event)

    async def close(self) -> None:
        await self.cmms.disconnect()


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


async def start_runtime(
    *, cmms_dir: Path, config_dir: Path, approver: Approver, sandbox: bool = True,
    channel: Any = None,
) -> CorvaneRuntime:
    """Connect machina's file-based CMMS connector and wire the engine."""
    cmms = GenericCmmsConnector(data_dir=cmms_dir)
    await cmms.connect()
    assets = {a.id: a for a in await cmms.read_assets()}
    services = CorvaneServices(
        assets=assets,
        failure_modes=await cmms.read_failure_modes(),
        history=await cmms.read_work_orders(),
        repair_kits=load_yaml(config_dir / "repair_kits.yaml"),
        alarm_parameters=load_yaml(config_dir / "alarm_parameters.yaml"),
        policy=load_yaml(config_dir / "priority_policy.yaml"),
        approver=approver,
    )
    registry = ConnectorRegistry()
    registry.register("cmms", cmms)
    registry.register("channel", channel or CliChannel())
    tracer = ActionTracer()
    # Mirror machina's Agent: the engine gates writes, and the contextvar makes
    # @sandbox_aware connector methods refuse writes as a second layer.
    set_sandbox_mode(sandbox)
    engine = WorkflowEngine(
        registry=registry,
        tracer=tracer,
        services={"corvane": services, "work_order_factory": WorkOrderFactory()},
        sandbox=sandbox,
    )
    return CorvaneRuntime(cmms=cmms, services=services, engine=engine, tracer=tracer,
                          sandbox=sandbox)


def summarize(result: WorkflowResult) -> dict[str, Any]:
    """Pull the fields the eval and demo care about out of a workflow result."""
    out: dict[str, Any] = {"success": result.success, "steps": []}
    by_name = {s.step_name: s for s in result.step_results}
    for s in result.step_results:
        state = "skipped" if s.skipped else ("ok" if s.success else f"error: {s.error}")
        out["steps"].append((s.step_name, state))
    draft = by_name.get("complete_draft")
    wo = draft.output if draft and draft.success and not draft.skipped else None
    out["work_order"] = wo
    out["failure_mode"] = wo.failure_mode if wo else None
    out["priority"] = wo.priority.value if wo else None
    out["parts"] = sorted((p.sku, p.qty) for p in wo.spare_parts) if wo else []
    approval = by_name.get("request_approval")
    out["approval"] = approval.output if approval and approval.success else None
    submit = by_name.get("submit_work_order")
    out["submit"] = (
        "skipped (not approved)" if submit and submit.skipped
        else "sandbox: intercepted, not written" if submit and isinstance(submit.output, dict)
        and submit.output.get("__sandbox__")
        else "written" if submit and submit.success else "not run"
    )
    return out

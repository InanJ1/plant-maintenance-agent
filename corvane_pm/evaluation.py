"""Evaluation on Corvane's synthetic alarms: Corvane workflow vs machina's built-in workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from machina import Agent, Plant
from machina.connectors.cmms import GenericCmmsConnector
from machina.connectors.comms.cli import CliChannel
from machina.workflows.builtins import alarm_to_workorder

from corvane_pm.approvals import no_approver
from corvane_pm.workflow import start_runtime, summarize


def load_alarms(path: Path) -> list[dict[str, Any]]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def expected_of(alarm: dict[str, Any]) -> dict[str, Any]:
    exp = alarm["expected"]
    return {"failure_mode": exp["failure_mode"], "priority": exp["priority"],
            "parts": sorted((sku, int(qty)) for sku, qty in exp["parts"])}


async def run_corvane(alarms: list[dict[str, Any]], *, cmms_dir: Path, config_dir: Path
                      ) -> list[dict[str, Any]]:
    runtime = await start_runtime(cmms_dir=cmms_dir, config_dir=config_dir,
                                  approver=no_approver(), sandbox=True)
    try:
        preds = []
        for alarm in alarms:
            event = {k: v for k, v in alarm.items() if k not in ("expected", "why")}
            s = summarize(await runtime.run_alarm(event))
            preds.append({"failure_mode": s["failure_mode"], "priority": s["priority"],
                          "parts": s["parts"], "submit": s["submit"]})
        return preds
    finally:
        await runtime.close()


async def run_baseline(alarms: list[dict[str, Any]], *, cmms_dir: Path) -> list[dict[str, Any]]:
    """machina's built-in alarm_to_workorder, unchanged, on the same Corvane data."""
    agent = Agent(
        name="Upstream baseline",
        plant=Plant(name="Corvane"),
        connectors=[GenericCmmsConnector(data_dir=cmms_dir)],
        channels=[CliChannel()],
        llm="ollama:unused",  # the built-in workflow never calls the LLM
        workflows=[alarm_to_workorder],
        sandbox=True,
        confirmations=False,
    )
    await agent.start()
    try:
        preds = []
        for alarm in alarms:
            result = await agent.trigger_workflow(alarm_to_workorder.name, {
                k: alarm[k] for k in ("alarm_id", "asset_id", "parameter", "value",
                                      "threshold", "severity")})
            wo = next((s.output for s in result.step_results
                       if s.step_name == "generate_work_order" and s.success), None)
            parts_listed = next((len(s.output or []) for s in result.step_results
                                 if s.step_name == "check_spare_parts" and s.success), 0)
            preds.append({
                "failure_mode": wo.failure_mode if wo else None,
                "priority": wo.priority.value if wo else None,
                "parts": sorted((p.sku, p.qty) for p in wo.spare_parts) if wo else [],
                "parts_listed_in_notification": parts_listed,
            })
        return preds
    finally:
        await agent.stop()


def score(alarms: list[dict[str, Any]], preds: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    totals = {"failure_mode": 0, "priority": 0, "parts": 0, "all_three": 0}
    for alarm, pred in zip(alarms, preds, strict=True):
        exp = expected_of(alarm)
        ok = {k: pred[k] == exp[k] for k in ("failure_mode", "priority", "parts")}
        ok["all_three"] = all(ok.values())
        for k, v in ok.items():
            totals[k] += int(v)
        rows.append({"alarm_id": alarm["alarm_id"], "asset_id": alarm["asset_id"],
                     "parameter": alarm["parameter"], "expected": exp, "predicted": pred,
                     "ok": ok, "why": alarm.get("why", "")})
    return {"n": len(rows), "totals": totals, "rows": rows}


def _parts(parts: list[tuple[str, int]]) -> str:
    return ", ".join(f"{sku} x{qty}" for sku, qty in parts) or "-"


def render_markdown(corvane: dict[str, Any], baseline: dict[str, Any]) -> str:
    n = corvane["n"]
    lines = [
        "# Evaluation: Corvane alarms",
        "",
        f"{n} synthetic alarms from `eval/alarms.yaml`. Produced by `python scripts/run_eval.py`.",
        "",
        "| Metric | Corvane workflow | machina built-in workflow |",
        "| --- | --- | --- |",
    ]
    for key, label in (("failure_mode", "Failure mode correct"), ("priority", "Priority correct"),
                       ("parts", "Required parts correct (exact SKU and qty)"),
                       ("all_three", "All three correct")):
        c, b = corvane["totals"][key], baseline["totals"][key]
        lines.append(f"| {label} | {c}/{n} ({100 * c // n}%) | {b}/{n} ({100 * b // n}%) |")
    lines += ["", "## Per alarm (Corvane workflow)", "",
              "| Alarm | Asset | Expected FM | Got FM | Exp. priority | Got | Exp. parts | Got parts |",
              "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in corvane["rows"]:
        e, p, ok = r["expected"], r["predicted"], r["ok"]
        mark = lambda good: "" if good else " **(miss)**"  # noqa: E731
        lines.append(
            f"| {r['alarm_id']} | {r['asset_id']} | {e['failure_mode'] or '-'} | "
            f"{p['failure_mode'] or '-'}{mark(ok['failure_mode'])} | {e['priority']} | "
            f"{p['priority']}{mark(ok['priority'])} | {_parts(e['parts'])} | "
            f"{_parts(p['parts'])}{mark(ok['parts'])} |")
    lines += ["", "## Misses (Corvane workflow)", ""]
    misses = [r for r in corvane["rows"] if not r["ok"]["all_three"]]
    for r in misses:
        wrong = [k for k in ("failure_mode", "priority", "parts") if not r["ok"][k]]
        lines.append(f"- {r['alarm_id']} ({r['asset_id']}, {r['parameter']}): wrong "
                     f"{', '.join(wrong)}. Expected {r['expected']['failure_mode']}, got "
                     f"{r['predicted']['failure_mode']}. Case note: {r['why']}")
    if not misses:
        lines.append("- none")
    lines += ["", "## Per alarm (machina built-in workflow)", "",
              "| Alarm | Got FM | Got priority | Parts on WO | Parts listed in notification |",
              "| --- | --- | --- | --- | --- |"]
    for r in baseline["rows"]:
        p, ok = r["predicted"], r["ok"]
        lines.append(f"| {r['alarm_id']} | {p['failure_mode'] or '-'}"
                     f"{'' if ok['failure_mode'] else ' (miss)'} | {p['priority']}"
                     f"{'' if ok['priority'] else ' (miss)'} | {_parts(p['parts'])} | "
                     f"{p.get('parts_listed_in_notification', 0)} |")
    return "\n".join(lines) + "\n"

"""Run Corvane's alarm-to-work-order workflow on a few alarms (sandbox mode).

    python scripts/run_alarm_demo.py                 # scripted planner answers (labelled)
    python scripts/run_alarm_demo.py --interactive   # you answer y/N for each draft
    python scripts/run_alarm_demo.py --alarms ALM-2610-001 ALM-2610-012

Sandbox mode is always on: the CMMS write and the notification are intercepted.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from corvane_pm.approvals import console_approver, render_draft, scripted_approver  # noqa: E402
from corvane_pm.config import CMMS_DIR, CONFIG_DIR, EVAL_FILE  # noqa: E402
from corvane_pm.evaluation import load_alarms  # noqa: E402
from corvane_pm.workflow import corvane_alarm_to_workorder, start_runtime, summarize  # noqa: E402

DEFAULT = ["ALM-2610-001", "ALM-2610-003", "ALM-2610-012", "ALM-2610-016"]
SCRIPTED_ANSWERS = [True, False, True, True, False]


async def main(alarm_ids: list[str], interactive: bool) -> None:
    by_id = {a["alarm_id"]: a for a in load_alarms(EVAL_FILE)}
    approver = console_approver() if interactive else scripted_approver(SCRIPTED_ANSWERS)
    runtime = await start_runtime(cmms_dir=CMMS_DIR, config_dir=CONFIG_DIR,
                                  approver=approver, sandbox=True)
    wf = corvane_alarm_to_workorder
    print(f"Workflow: {wf.name} ({len(wf.steps)} steps) | mode: SANDBOX | approvals: "
          f"{'console' if interactive else 'scripted ' + str(SCRIPTED_ANSWERS)}")
    try:
        for alarm_id in alarm_ids:
            alarm = {k: v for k, v in by_id[alarm_id].items() if k not in ("expected", "why")}
            print("\n" + "=" * 78)
            print(f"{alarm_id}  {alarm['asset_id']}  {alarm['parameter']}={alarm['value']} "
                  f"(limit {alarm['threshold']}, {alarm['severity']})  "
                  f"related={alarm.get('related_readings') or {}}")
            result = await runtime.run_alarm(alarm)
            s = summarize(result)
            print(f"result: {'SUCCESS' if result.success else 'FAILED'} in "
                  f"{result.duration_ms:.0f} ms")
            for name, state in s["steps"]:
                print(f"  [{'+' if state == 'ok' else '~' if state == 'skipped' else 'x'}] "
                      f"{name:<18} {state}")
            if s["work_order"] is not None:
                print(render_draft(s["work_order"]))
            a = s["approval"] or {}
            print(f"  Approval:       approved={a.get('approved')} by {a.get('approver')!r} "
                  f"({a.get('mode')}: {a.get('note')})")
            print(f"  CMMS submit:    {s['submit']}")
    finally:
        await runtime.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--alarms", nargs="+", default=DEFAULT)
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--verbose", action="store_true", help="show machina's engine log")
    args = parser.parse_args()
    from machina.observability.logging import configure_logging

    configure_logging(level="INFO" if args.verbose else "WARNING")
    asyncio.run(main(args.alarms, args.interactive))

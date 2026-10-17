from __future__ import annotations

import json

import pytest

from corvane_pm.approvals import no_approver, scripted_approver
from corvane_pm.config import CONFIG_DIR
from corvane_pm.workflow import corvane_alarm_to_workorder, start_runtime, summarize
from tests.conftest import event


class FakeChannel:
    capabilities = frozenset({"send_message"})

    def __init__(self):
        self.sent = []

    async def connect(self):
        pass

    async def disconnect(self):
        pass

    async def send_message(self, channel, text):
        self.sent.append(text)


def test_every_step_declares_is_write():
    # machina's write heuristic would gate "assess_priority" ("set") and
    # "complete_draft" ("complete"); explicit flags keep sandbox runs honest.
    steps = corvane_alarm_to_workorder.steps
    assert all(s.is_write is not None for s in steps)
    assert {s.name for s in steps if s.is_write} == {"submit_work_order", "notify_technician"}
    assert all(s.guard is not None for s in steps if s.is_write)


async def _run(cmms_dir, alarm, approver, sandbox=True, channel=None):
    rt = await start_runtime(cmms_dir=cmms_dir, config_dir=CONFIG_DIR, approver=approver,
                             sandbox=sandbox, channel=channel)
    try:
        return summarize(await rt.run_alarm(alarm))
    finally:
        await rt.close()


async def test_unapproved_draft_is_not_submitted(built, alarms):
    s = await _run(built[0], event(alarms["ALM-2610-001"]), no_approver())
    assert s["success"]
    assert s["failure_mode"] == "CNC-SPBRG-WEAR"
    assert s["submit"] == "skipped (not approved)"
    assert dict(s["steps"])["notify_technician"] == "skipped"


async def test_approved_draft_is_intercepted_in_sandbox(built, alarms):
    s = await _run(built[0], event(alarms["ALM-2610-001"]), scripted_approver([True]))
    assert s["approval"]["approved"] is True
    assert s["submit"] == "sandbox: intercepted, not written"


async def test_live_mode_writes_only_after_approval(cmms_copy, alarms):
    path = cmms_copy / "work_orders.json"
    before = len(json.loads(path.read_text(encoding="utf-8")))
    s = await _run(cmms_copy, event(alarms["ALM-2610-013"]), no_approver(), sandbox=False,
                   channel=FakeChannel())
    assert s["submit"] == "skipped (not approved)"
    assert len(json.loads(path.read_text(encoding="utf-8"))) == before

    channel = FakeChannel()
    s = await _run(cmms_copy, event(alarms["ALM-2610-013"]), scripted_approver([True]),
                   sandbox=False, channel=channel)
    assert s["submit"] == "written"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert len(saved) == before + 1
    new = next(w for w in saved if w["id"] == s["work_order"].id)
    assert new["spare_parts"] == [{"sku": "SP-FLT-0501", "qty": 1}]
    assert channel.sent and "CMP-01" in channel.sent[0]


async def test_info_alarms_do_not_trigger(built, alarms):
    alarm = {**event(alarms["ALM-2610-013"]), "severity": "info"}
    with pytest.raises(ValueError):
        await _run(built[0], alarm, no_approver())


async def test_unknown_asset_stops_at_diagnose(built, alarms):
    alarm = {**event(alarms["ALM-2610-013"]), "asset_id": "CMP-09"}
    s = await _run(built[0], alarm, no_approver())
    assert not s["success"]
    assert s["steps"][0][1].startswith("error")
    assert s["work_order"] is None


async def test_diagnosis_is_scoped_to_asset_and_uses_related_readings(built, alarms):
    rt = await start_runtime(cmms_dir=built[0], config_dir=CONFIG_DIR, approver=no_approver())
    svc = rt.services
    try:
        a = alarms["ALM-2610-010"]
        with_related = svc.diagnose(asset_id="CMP-01", parameter=a["parameter"], value=a["value"],
                                    related_readings=a["related_readings"])
        alone = svc.diagnose(asset_id="CMP-01", parameter=a["parameter"], value=a["value"])
        assert with_related.primary_code == "CMP-TVALVE"
        assert alone.primary_code == "CMP-COOLER-FOUL"  # more frequent in RS-75 history
        assert all(code.startswith("CMP-") for code in alone.codes)
        assert svc.diagnose(asset_id="CST-01", parameter="pour_temp_deviation_c",
                            value=31).primary_code is None
    finally:
        await rt.close()


async def test_priority_policy_escalations(built, alarms):
    trip = await _run(built[0], event(alarms["ALM-2610-006"]), no_approver())
    assert trip["priority"] == "emergency"  # A + past trip limit
    repeat = await _run(built[0], event(alarms["ALM-2610-020"]), no_approver())
    assert repeat["priority"] == "high"  # B + warning = medium, raised by repeat failure
    assert any("repeat" in r for r in repeat["work_order"].metadata["priority_reasons"])


async def test_parts_shortfall_flagged(built, alarms):
    s = await _run(built[0], event(alarms["ALM-2610-003"]), no_approver())
    meta = s["work_order"].metadata
    assert meta["parts_hold"] is True
    assert any("SP-BRG-0116" in x for x in meta["parts_shortfalls"])

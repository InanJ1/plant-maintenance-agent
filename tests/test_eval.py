from __future__ import annotations

from corvane_pm.config import CONFIG_DIR
from corvane_pm.evaluation import render_markdown, run_baseline, run_corvane, score


def _alarm(fm, prio, parts):
    return {"alarm_id": "A1", "asset_id": "X", "parameter": "p",
            "expected": {"failure_mode": fm, "priority": prio, "parts": parts}}


def test_score_counts_each_field():
    alarms = [_alarm("F1", "high", [["S1", 1]]), _alarm(None, "low", [])]
    preds = [{"failure_mode": "F1", "priority": "medium", "parts": [("S1", 1)]},
             {"failure_mode": None, "priority": "low", "parts": []}]
    s = score(alarms, preds)
    assert s["totals"] == {"failure_mode": 2, "priority": 1, "parts": 2, "all_three": 1}
    assert s["rows"][0]["ok"]["priority"] is False


def test_eval_set_shape(alarms):
    assert 15 <= len(alarms) <= 20
    for a in alarms.values():
        assert a["expected"]["priority"] in {"low", "medium", "high", "emergency"}


async def test_eval_reproduces_reported_numbers(built, alarms):
    """Locks the README numbers: change data or policy and this test says so."""
    cases = list(alarms.values())
    corvane = score(cases, await run_corvane(cases, cmms_dir=built[0], config_dir=CONFIG_DIR))
    baseline = score(cases, await run_baseline(cases, cmms_dir=built[0]))
    assert corvane["totals"] == {"failure_mode": 17, "priority": 20, "parts": 18, "all_three": 17}
    assert baseline["totals"] == {"failure_mode": 14, "priority": 6, "parts": 4, "all_three": 0}
    misses = [r["alarm_id"] for r in corvane["rows"] if not r["ok"]["all_three"]]
    assert misses == ["ALM-2610-005", "ALM-2610-011", "ALM-2610-016"]
    assert "| Failure mode correct | 17/20" in render_markdown(corvane, baseline)

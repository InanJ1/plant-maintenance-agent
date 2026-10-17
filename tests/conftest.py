from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from machina.connectors.base import set_sandbox_mode

from corvane_pm.config import CONFIG_DIR, EVAL_FILE, RAW_DIR
from corvane_pm.data_loader import build_cmms_dir
from corvane_pm.evaluation import load_alarms


@pytest.fixture(autouse=True)
def _reset_sandbox():
    set_sandbox_mode(False)
    yield
    set_sandbox_mode(False)


@pytest.fixture(scope="session")
def built(tmp_path_factory):
    """Raw exports -> machina CMMS dir, built once per test session."""
    out = tmp_path_factory.mktemp("cmms")
    report = build_cmms_dir(RAW_DIR, CONFIG_DIR, out)
    return out, report


@pytest.fixture
def cmms_copy(built, tmp_path) -> Path:
    """A private copy for tests that write work orders."""
    dst = tmp_path / "cmms"
    shutil.copytree(built[0], dst)
    return dst


@pytest.fixture(scope="session")
def alarms():
    return {a["alarm_id"]: a for a in load_alarms(EVAL_FILE)}


def event(alarm: dict) -> dict:
    return {k: v for k, v in alarm.items() if k not in ("expected", "why")}

from __future__ import annotations

import csv
import json
from datetime import date

import pytest
from machina.connectors.cmms import GenericCmmsConnector

from corvane_pm.config import CONFIG_DIR, RAW_DIR
from corvane_pm.data_loader import build_cmms_dir, normalize_asset_id, parse_date, parse_parts

FORMATS = {"IND1": "%m/%d/%Y", "MTY1": "%d/%m/%Y"}


@pytest.mark.parametrize("raw,expected", [
    ("CNC 4", "CNC-04"), ("cnc-04", "CNC-04"), ("CNC-04 ", "CNC-04"), ("CMP-3", "CMP-03"),
    ("IND1", "IND1"), ("mty1-util", "MTY1-UTIL"),
])
def test_normalize_asset_id(raw, expected):
    assert normalize_asset_id(raw) == expected


def test_parse_date_per_site():
    assert parse_date("2026-03-05", "MTY1", FORMATS) == date(2026, 3, 5)
    assert parse_date("05/03/2026", "IND1", FORMATS) == date(2026, 5, 3)
    assert parse_date("05/03/2026", "MTY1", FORMATS) == date(2026, 3, 5)
    assert parse_date("", "IND1", FORMATS) is None
    with pytest.raises(ValueError):
        parse_date("05/03/2026", "XXX1", FORMATS)


def test_parse_parts():
    assert parse_parts("SP-BRG-0114x1;SP-SEAL-0207x2") == [
        {"sku": "SP-BRG-0114", "qty": 1}, {"sku": "SP-SEAL-0207", "qty": 2}]
    assert parse_parts("") == []
    with pytest.raises(ValueError):
        parse_parts("bearing")


def _load(out, name):
    return json.loads((out / f"{name}.json").read_text(encoding="utf-8"))


def test_build_counts_and_report(built):
    out, report = built
    assert report.counts["assets"] == 29
    assert report.counts["work_orders"] == 220  # 223 rows minus 3 duplicates
    assert report.counts["failure_modes"] == 18
    assert report.fixes["duplicate work-order rows dropped"] == 3
    assert any("TST-03" in w for w in report.warnings)


def test_work_orders_clean_and_newest_first(built):
    out, _ = built
    assets = {a["id"] for a in _load(out, "assets")}
    wos = _load(out, "work_orders")
    assert len({w["id"] for w in wos}) == len(wos)
    assert all(w["asset_id"] in assets for w in wos)
    dates = [w["updated_at"] for w in wos]
    assert dates == sorted(dates, reverse=True)
    assert all(w["description"].startswith("[20") for w in wos)


def test_spare_parts_scoped_to_site_and_usd(built):
    out, _ = built
    parts = _load(out, "spare_parts")
    hx = next(p for p in parts if p["sku"] == "SP-BRG-0116")
    assert hx["compatible_assets"] == ["CNC-06", "CNC-07", "CNC-08"]
    seal_mty = next(p for p in parts if p["sku"] == "SP-SEAL-0207"
                    and p["warehouse_location"].startswith("MTY1"))
    assert seal_mty["unit_cost"] == 145.0  # 2610 MXN / 18
    assert {p["manufacturer"] for p in parts} <= {
        "Brightline Bearings", "Pellum Seal Co.", "Keystone MRO Supply",
        "Ostrava Motor Works", "Tolland Air Systems", "Varnell Machine Works"}


def test_assets_get_catalog_failure_modes(built):
    out, _ = built
    assets = {a["id"]: a for a in _load(out, "assets")}
    assert "CNC-SPBRG-WEAR" in assets["CNC-04"]["failure_modes"]
    assert all(c.startswith("CMP-") for c in assets["CMP-03"]["failure_modes"])
    assert assets["CST-01"]["failure_modes"] == []
    assert assets["TST-03"]["criticality"] == "B"
    assert assets["CMP-01"]["equipment_class_code"] == "CO"


async def test_output_loads_in_machina_connector(built):
    conn = GenericCmmsConnector(data_dir=built[0])
    await conn.connect()
    assert len(await conn.read_assets()) == 29
    assert len(await conn.read_failure_modes()) == 18
    stock = await conn.read_spare_parts(asset_id="CNC-07")
    assert {p.sku for p in stock} >= {"SP-BRG-0116", "SP-SEAL-0207"}
    history = await conn.read_maintenance_history("CMP-03")
    assert history and all(w.status.value in ("completed", "closed") for w in history)


def test_unknown_equipment_rows_dropped(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    for name in ("cmms_assets.csv", "erp_spare_parts.csv"):
        (raw / name).write_bytes((RAW_DIR / name).read_bytes())
    with (RAW_DIR / "cmms_work_orders.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    rows = rows[:5]
    rows.append({**rows[0], "WONum": "IND1-269999", "Equipment": "PRESS-9"})
    with (raw / "cmms_work_orders.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report = build_cmms_dir(raw, CONFIG_DIR, tmp_path / "out")
    assert report.counts["work_orders"] == 5
    assert any("PRESS-9" in w for w in report.warnings)

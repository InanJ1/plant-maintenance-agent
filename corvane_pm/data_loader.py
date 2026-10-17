"""Load Corvane's CMMS/ERP CSV exports into machina's local CMMS layout.

machina's ``GenericCmmsConnector(data_dir=...)`` reads a directory of JSON files
(``assets.json``, ``work_orders.json``, ``spare_parts.json``,
``failure_modes.json``). Corvane's systems export CSV with their own column
names, codes and quirks, so this module is the adapter between the two:

- normalizes equipment IDs typed by hand ("CNC 4", "cnc-04" -> "CNC-04")
- parses dates per site (IND1 month-first, MTY1 day-first, ISO everywhere)
- maps CMMS status, priority and work-type codes onto machina enums
- drops duplicated work-order rows and rows for unknown equipment
- links spare parts to assets through the "FitsModels" column and the storeroom site
- converts MTY1 unit costs from MXN to USD
- fills ``Asset.failure_modes`` from the reliability catalog (by machine model)

Every record is validated through machina's own pydantic models before it is
written, so a bad export fails here instead of inside the agent.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml
from machina.domain.asset import Asset
from machina.domain.failure_mode import FailureMode
from machina.domain.spare_part import SparePart
from machina.domain.work_order import WorkOrder

# Corvane equipment prefixes. Site and area codes (IND1, MTY1-UTIL) are left alone.
_ID_RE = re.compile(r"^\s*(CNC|CMP|TST|CNV|CST)[\s\-_]*0*(\d{1,2})\s*$", re.IGNORECASE)
_PART_RE = re.compile(r"^\s*(SP-[A-Z]+-\d{4})\s*x\s*(\d+)\s*$")


@dataclass
class LoadReport:
    """What the loader changed or rejected, for the data-quality log."""

    counts: dict[str, int] = field(default_factory=dict)
    fixes: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def fix(self, kind: str) -> None:
        self.fixes[kind] = self.fixes.get(kind, 0) + 1

    def render(self) -> str:
        lines = ["Corvane data load report", "", "Records written:"]
        lines += [f"  {k}: {v}" for k, v in self.counts.items()]
        lines += ["", "Fixes applied:"]
        lines += [f"  {k}: {v}" for k, v in sorted(self.fixes.items())] or ["  none"]
        lines += ["", "Warnings:"]
        lines += [f"  {w}" for w in self.warnings] or ["  none"]
        return "\n".join(lines)


def normalize_asset_id(raw: str) -> str:
    """Return the canonical ``PFX-NN`` form of a hand-typed equipment ID.

    IDs that do not look like equipment (sites, areas) are returned stripped
    and upper-cased.
    """
    match = _ID_RE.match(raw or "")
    if match:
        return f"{match.group(1).upper()}-{int(match.group(2)):02d}"
    return (raw or "").strip().upper()


def parse_date(raw: str, site: str, site_formats: dict[str, str]) -> date | None:
    """Parse an export date: ISO first, then the site's own format."""
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        pass
    fmt = site_formats.get(site)
    if fmt is None:
        raise ValueError(f"no date format configured for site {site!r}: {text!r}")
    return datetime.strptime(text, fmt).date()


def parse_parts(raw: str) -> list[dict[str, Any]]:
    """Parse ``"SP-BRG-0114x1;SP-SEAL-0207x1"`` into ``[{sku, qty}, ...]``."""
    parts = []
    for item in (raw or "").split(";"):
        if not item.strip():
            continue
        match = _PART_RE.match(item)
        if not match:
            raise ValueError(f"cannot parse parts entry {item!r}")
        parts.append({"sku": match.group(1), "qty": int(match.group(2))})
    return parts


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def _read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_failure_modes(config_dir: Path) -> tuple[list[FailureMode], dict[str, list[str]]]:
    """Return the catalog and a ``model -> [failure-mode codes]`` index."""
    catalog = _read_yaml(config_dir / "failure_modes.yaml")
    modes: list[FailureMode] = []
    by_model: dict[str, list[str]] = {}
    for item in catalog:
        models = item.pop("applies_to_models", [])
        fm = FailureMode(**item)
        modes.append(fm)
        for model in models:
            by_model.setdefault(model, []).append(fm.code)
    return modes, by_model


def build_assets(
    rows: list[dict[str, str]], mapping: dict[str, Any], fm_by_model: dict[str, list[str]],
    report: LoadReport,
) -> list[Asset]:
    names = {normalize_asset_id(r["EquipmentID"]): r["Description"].strip() for r in rows}
    assets: list[Asset] = []
    for row in rows:
        asset_id = normalize_asset_id(row["EquipmentID"])
        site = row["Site"].strip().upper()
        cls = mapping["asset_class"][row["Class"].strip().upper()]
        parent = normalize_asset_id(row["ParentID"]) or None
        crit = row["Criticality"].strip().upper()
        if not crit:
            crit = mapping["default_criticality"]
            report.fix("asset criticality blank, defaulted")
            report.warnings.append(
                f"{asset_id}: criticality blank in CMMS export, used {crit}; confirm with planner"
            )
        make = row["Make"].strip()
        if make != row["Make"]:
            report.fix("asset make whitespace trimmed")
        install = parse_date(row["InstallDate"], site, mapping["site_date_format"])
        model = row["Model"].strip()
        location = " / ".join(
            dict.fromkeys(names[p] for p in (site, parent) if p and p in names and p != asset_id)
        )
        asset = Asset(
            id=asset_id,
            name=row["Description"].strip(),
            type=cls["type"],
            location=location,
            manufacturer=make,
            model=model,
            serial_number=row["SerialNo"].strip(),
            install_date=install,
            criticality=crit,
            parent=parent if parent != asset_id else None,
            failure_modes=fm_by_model.get(model, []),
            equipment_class_code=cls.get("iso_class"),
            metadata={
                "site": site,
                "cmms_class": row["Class"].strip().upper(),
                "install_date": install.isoformat() if install else "",
                "status": row["Status"].strip(),
            },
        )
        assets.append(asset)
    by_id = {a.id: a for a in assets}
    for asset in assets:
        if asset.parent and asset.parent in by_id:
            by_id[asset.parent].children.append(asset.id)
    return assets


def build_work_orders(
    rows: list[dict[str, str]], mapping: dict[str, Any], assets: dict[str, Asset],
    fm_codes: set[str], report: LoadReport,
) -> list[WorkOrder]:
    seen: set[str] = set()
    orders: list[tuple[date, WorkOrder]] = []
    for row in rows:
        wonum = row["WONum"].strip()
        if wonum in seen:
            report.fix("duplicate work-order rows dropped")
            continue
        seen.add(wonum)
        asset_id = normalize_asset_id(row["Equipment"])
        if asset_id != row["Equipment"]:
            report.fix("work-order equipment ID normalized")
        if asset_id not in assets:
            report.fix("work orders for unknown equipment dropped")
            report.warnings.append(f"{wonum}: unknown equipment {row['Equipment']!r}, dropped")
            continue
        site = assets[asset_id].metadata["site"]
        reported = parse_date(row["Reported"], site, mapping["site_date_format"])
        completed = parse_date(row["Completed"], site, mapping["site_date_format"])
        if reported is None:
            report.warnings.append(f"{wonum}: no reported date, dropped")
            continue
        if not _is_iso(row["Reported"]):
            report.fix("site-format dates converted to ISO")
        code = row["FailureCode"].strip() or None
        if code and code not in fm_codes:
            report.warnings.append(f"{wonum}: failure code {code!r} not in catalog, cleared")
            code = None
        wo_type = mapping["work_type"][row["WOType"].strip().upper()]
        if wo_type == "corrective" and code is None:
            report.fix("corrective work orders without failure code (kept)")
        hours = row["LaborHrs"].strip()
        if not hours:
            report.fix("labor hours blank (kept as unknown)")
        when = completed or reported
        # machina's prompt formatter shows only the first 80 characters of a
        # work-order description and no dates, so the date goes first.
        description = f"[{when.isoformat()}] {row['ProblemDesc'].strip()}"
        wo = WorkOrder(
            id=wonum,
            type=wo_type,
            priority=mapping["priority"][row["Priority"].strip()],
            status=mapping["status"][row["Status"].strip().upper()],
            asset_id=asset_id,
            description=description,
            failure_mode=code,
            spare_parts=parse_parts(row["PartsUsed"]),
            estimated_duration_hours=float(hours) if hours else None,
            assigned_to=row["Technician"].strip() or None,
            created_at=datetime(reported.year, reported.month, reported.day, tzinfo=UTC),
            updated_at=datetime(when.year, when.month, when.day, tzinfo=UTC),
            metadata={
                "site": site,
                "reported_date": reported.isoformat(),
                "completed_date": completed.isoformat() if completed else "",
                "downtime_hours": float(row["DowntimeHrs"]) if row["DowntimeHrs"].strip() else None,
            },
        )
        orders.append((when, wo))
    # Newest first: machina's prompt context lists the first 10 work orders
    # it finds for an asset, so file order decides which ones the LLM sees.
    orders.sort(key=lambda pair: (pair[0], pair[1].id), reverse=True)
    return [wo for _, wo in orders]


def build_spare_parts(
    rows: list[dict[str, str]], mapping: dict[str, Any], assets: list[Asset],
    report: LoadReport,
) -> list[SparePart]:
    parts: list[SparePart] = []
    aliases = {k.lower(): v for k, v in mapping["vendor_aliases"].items()}
    for row in rows:
        site = mapping["storeroom_site"][row["Storeroom"].strip()]
        fits = {m.strip() for m in row["FitsModels"].split(";") if m.strip()}
        compatible = sorted(
            a.id for a in assets if a.model in fits and a.metadata.get("site") == site
        )
        if not compatible:
            report.warnings.append(f"{row['ItemNo']} @ {row['Storeroom']}: fits no asset")
        supplier_raw = row["Supplier"].strip()
        supplier = aliases.get(supplier_raw.lower(), supplier_raw)
        if supplier != supplier_raw:
            report.fix("supplier name variants canonicalized")
        cost = float(row["UnitCost"])
        if row["Currency"].strip().upper() == "MXN":
            cost = round(cost / float(mapping["mxn_per_usd"]), 2)
            report.fix("MXN unit costs converted to USD")
        parts.append(
            SparePart(
                sku=row["ItemNo"].strip(),
                name=row["ItemDesc"].strip(),
                manufacturer=supplier,
                compatible_assets=compatible,
                stock_quantity=int(row["OnHand"]),
                reorder_point=int(row["ReorderPt"]),
                lead_time_days=int(row["LeadTimeDays"]),
                unit_cost=cost,
                warehouse_location=f"{row['Storeroom'].strip()}/{row['BinLoc'].strip()}",
            )
        )
    return parts


def _is_iso(raw: str) -> bool:
    try:
        date.fromisoformat(raw.strip())
    except ValueError:
        return False
    return True


def build_cmms_dir(raw_dir: Path, config_dir: Path, out_dir: Path) -> LoadReport:
    """Convert the raw exports in ``raw_dir`` into ``out_dir`` for GenericCmmsConnector."""
    report = LoadReport()
    mapping = _read_yaml(config_dir / "data_mapping.yaml")
    failure_modes, fm_by_model = load_failure_modes(config_dir)
    assets = build_assets(_read_csv(raw_dir / "cmms_assets.csv"), mapping, fm_by_model, report)
    asset_index = {a.id: a for a in assets}
    work_orders = build_work_orders(
        _read_csv(raw_dir / "cmms_work_orders.csv"), mapping, asset_index,
        {fm.code for fm in failure_modes}, report,
    )
    spare_parts = build_spare_parts(
        _read_csv(raw_dir / "erp_spare_parts.csv"), mapping, assets, report
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    _dump(out_dir / "assets.json", [a.model_dump(mode="json") for a in assets])
    _dump(out_dir / "work_orders.json", [w.model_dump(mode="json") for w in work_orders])
    _dump(out_dir / "spare_parts.json", [p.model_dump(mode="json") for p in spare_parts])
    _dump(out_dir / "failure_modes.json", [f.model_dump(mode="json") for f in failure_modes])
    report.counts = {
        "assets": len(assets),
        "work_orders": len(work_orders),
        "spare_parts (sku x storeroom)": len(spare_parts),
        "failure_modes": len(failure_modes),
    }
    return report


def _dump(path: Path, data: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

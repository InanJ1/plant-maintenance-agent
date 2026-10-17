"""Generate Corvane's synthetic CMMS and ERP exports (seed 42).

Writes three CSV files into data/raw/, shaped like the exports Corvane's
systems produce, including their messiness:

- cmms_assets.csv       asset register for IND1 and MTY1
- cmms_work_orders.csv  work-order history, Jan 2025 - Sep 2026
- erp_spare_parts.csv   spare-parts stock per plant storeroom

Messiness on purpose: equipment IDs typed inconsistently ("CNC 4", "cnc-04"),
MTY1 dates exported day-first, a blank criticality, duplicated rows, blank
failure codes and labor hours, supplier-name typos, MTY1 costs in MXN.

Run: python scripts/generate_data.py
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 42
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

HISTORY_START = date(2025, 1, 6)
BACKGROUND_END = date(2026, 6, 30)  # random corrective work stops here
HISTORY_END = date(2026, 9, 30)

# --------------------------------------------------------------------------
# Asset register
# --------------------------------------------------------------------------

AREAS = [
    ("IND1-MACH", "IND1 machining hall", "IND1"),
    ("IND1-UTIL", "IND1 utilities and compressor room", "IND1"),
    ("IND1-TEST", "IND1 pump test bay", "IND1"),
    ("IND1-MATL", "IND1 material handling", "IND1"),
    ("IND1-CAST", "IND1 casting line area", "IND1"),
    ("MTY1-MACH", "MTY1 machining hall", "MTY1"),
    ("MTY1-UTIL", "MTY1 utilities and compressor room", "MTY1"),
    ("MTY1-TEST", "MTY1 pump test bay", "MTY1"),
    ("MTY1-MATL", "MTY1 material handling", "MTY1"),
]

# id, description, class, area, make, model, criticality
EQUIPMENT = [
    ("CNC-01", "VMC 01 - CP-400 casings", "CNC", "IND1-MACH", "Varnell Machine Works", "VX-640", "A"),
    ("CNC-02", "VMC 02 - CP-400 casings", "CNC", "IND1-MACH", "Varnell Machine Works", "VX-640", "A"),
    ("CNC-03", "VMC 03 - CP-200 casings", "CNC", "IND1-MACH", "Varnell Machine Works", "VX-640", "A"),
    ("CNC-04", "VMC 04 - impellers", "CNC", "IND1-MACH", "Varnell Machine Works", "VX-640", "B"),
    ("CNC-05", "VMC 05 - impellers", "CNC", "IND1-MACH", "Varnell Machine Works", "VX-640", "B"),
    ("CNC-06", "HMC 06 - GB-40 housings", "CNC", "MTY1-MACH", "Varnell Machine Works", "HX-500", "A"),
    ("CNC-07", "HMC 07 - GB-20 housings", "CNC", "MTY1-MACH", "Varnell Machine Works", "HX-500", "B"),
    ("CNC-08", "HMC 08 - GB-20 housings", "CNC", "MTY1-MACH", "Varnell Machine Works", "HX-500", "B"),
    ("CMP-01", "Air compressor 01 (lead)", "COMPRESSOR", "IND1-UTIL", "Tolland Air Systems", "RS-75", "B"),
    ("CMP-02", "Air compressor 02 (lag)", "COMPRESSOR", "IND1-UTIL", "Tolland Air Systems", "RS-75", "B"),
    ("CMP-03", "Air compressor 03 (single unit)", "COMPRESSOR", "MTY1-UTIL", "Tolland Air Systems", "RS-75", "A"),
    ("TST-01", "Pump test stand 01", "TESTSTAND", "IND1-TEST", "Corvane Industrial", "PTS-2", "B"),
    ("TST-02", "Pump test stand 02", "TESTSTAND", "IND1-TEST", "Corvane Industrial", "PTS-2", "B"),
    ("TST-03", "Pump test stand 03", "TESTSTAND", "MTY1-TEST", "Corvane Industrial", "PTS-2", ""),
    ("CNV-01", "Casting-to-machining conveyor", "CONVEYOR", "IND1-MATL", "Arden Conveyor Co.", "RC-1200", "C"),
    ("CNV-02", "Machining-to-test conveyor", "CONVEYOR", "IND1-MATL", "Arden Conveyor Co.", "RC-1200", "C"),
    ("CNV-03", "Machining-to-test conveyor", "CONVEYOR", "MTY1-MATL", "Arden Conveyor Co.", "RC-1200", "C"),
    ("CST-01", "Casting line 1", "CASTING", "IND1-CAST", "Corvane Industrial", "CL-1", "A"),
]

# --------------------------------------------------------------------------
# Work-order history
# --------------------------------------------------------------------------

# Corrective jobs per machine model and failure mode over Jan 2025 - Jun 2026.
# Fixed counts (dates and assets are random) so the history-frequency
# tie-break in the workflow is stable and easy to explain.
CORRECTIVE_COUNTS = {
    "VX-640": {"CNC-SPIMB": 7, "CNC-COOL": 6, "CNC-SPBRG-WEAR": 4, "CNC-SPLUB": 3,
               "CNC-DBAR": 2, "CNC-SPMOT": 1, "": 2},
    "HX-500": {"CNC-SPBRG-WEAR": 3, "CNC-COOL": 3, "CNC-SPIMB": 2, "CNC-SPLUB": 2,
               "CNC-SPMOT": 2, "CNC-DBAR": 1},
    "RS-75": {"CMP-COOLER-FOUL": 5, "CMP-INFLT-CLOG": 4, "CMP-SEP-SAT": 3, "CMP-AIRLEAK": 3,
              "CMP-TVALVE": 2, "CMP-OILFLT": 2, "CMP-SHAFTSEAL": 2, "CMP-MOTBRG": 1, "": 1},
    "RC-1200": {"CNV-ROLLER": 4, "CNV-MISTRACK": 3},
    "PTS-2": {"TST-SEAL": 3, "TST-FLOWMETER": 2},
}

# Two scripted recent jobs that the evaluation relies on (repeat-failure policy).
SCRIPTED = [
    # asset, failure code, completed date, text, parts
    ("CMP-03", "CMP-SEP-SAT", date(2026, 8, 12),
     "Separator dP 1.0 bar and oil in the air lines. Replaced air/oil separator element.",
     "SP-SEP-0503x1"),
    ("CNC-05", "CNC-COOL", date(2026, 8, 28),
     "Low coolant pressure at the spindle nozzles. Changed both coolant filter cartridges.",
     "SP-FLT-0310x2"),
]

PROBLEM_TEXT = {
    "CNC-SPIMB": [
        "Vibration high at 9000 rpm with one toolholder. Cleaned taper, rebalanced holder.",
        "Chatter marks on impeller vanes. Toolholder out of balance, replaced holder.",
    ],
    "CNC-COOL": [
        "Low coolant pressure at the spindle nozzles. Changed both coolant filter cartridges.",
        "Coolant filter dP alarm. Replaced cartridges and skimmed tank.",
    ],
    "CNC-SPBRG-WEAR": [
        "Spindle noisy and hot. Bearing defect on envelope check. Replaced bearing set and seal.",
        "Spindle vibration rising for 3 weeks. Rebuilt spindle: bearings and labyrinth seal.",
    ],
    "CNC-SPLUB": [
        "Spindle temperature high, lube pressure low. Replaced lube cartridge and line filter.",
        "Oil-air lube fault. Air in lines, bled lines and replaced cartridge.",
    ],
    "CNC-DBAR": [
        "Tool pulled out during roughing. Clamp force 13 kN. Replaced disc spring stack.",
    ],
    "CNC-SPMOT": [
        "Spindle motor overtemp. Cooling fan seized, replaced fan.",
    ],
    "CMP-COOLER-FOUL": [
        "Discharge temp 107 C in afternoon heat. Cooler fins blocked with dust, cleaned cooler.",
        "High discharge temperature trip. Cleaned cooler core, checked fan.",
    ],
    "CMP-INFLT-CLOG": [
        "Intake filter dP high. Replaced intake filter element.",
    ],
    "CMP-SEP-SAT": [
        "Separator dP high and oil carryover. Replaced air/oil separator element.",
    ],
    "CMP-AIRLEAK": [
        "Header pressure low with compressor fully loaded. Leak survey found 6 leaks, repaired.",
    ],
    "CMP-TVALVE": [
        "Discharge temp high but cooler clean. Thermostatic valve stuck in bypass, replaced element.",
    ],
    "CMP-OILFLT": [
        "Oil filter dP alarm. Replaced oil filter element.",
    ],
    "CMP-SHAFTSEAL": [
        "Oil under airend coupling, level dropping. Replaced shaft seal kit, topped up fluid.",
    ],
    "CMP-MOTBRG": [
        "Motor vibration 7.5 mm/s, bearing noise. Replaced motor bearings, checked alignment.",
    ],
    "CNV-ROLLER": [
        "Grinding noise at tail section. Replaced two roller bearings.",
    ],
    "CNV-MISTRACK": [
        "Belt drifting to drive side. Adjusted tracking idlers.",
    ],
    "TST-SEAL": [
        "Leak at loop pump seal. Replaced mechanical seal.",
    ],
    "TST-FLOWMETER": [
        "Flowmeter reads 2 percent high vs reference. Recalibrated.",
    ],
    "": [
        "Machine stopped, reset and returned to production. Cause not recorded.",
        "Operator reported abnormal noise. Inspected, nothing found.",
    ],
}

PARTS_USED = {
    ("CNC-SPBRG-WEAR", "VX-640"): "SP-BRG-0114x1;SP-SEAL-0207x1",
    ("CNC-SPBRG-WEAR", "HX-500"): "SP-BRG-0116x1;SP-SEAL-0207x1",
    ("CNC-SPLUB", "VX-640"): "SP-LUB-0402x1;SP-FLT-0405x1",
    ("CNC-SPLUB", "HX-500"): "SP-LUB-0402x1;SP-FLT-0405x1",
    ("CNC-DBAR", "VX-640"): "SP-SPRG-0031x1",
    ("CNC-DBAR", "HX-500"): "SP-SPRG-0031x1",
    ("CNC-COOL", "VX-640"): "SP-FLT-0310x2",
    ("CNC-COOL", "HX-500"): "SP-FLT-0310x2",
    ("CNC-SPMOT", "VX-640"): "SP-FAN-0044x1",
    ("CNC-SPMOT", "HX-500"): "SP-FAN-0044x1",
    ("CMP-TVALVE", "RS-75"): "SP-VLV-0520x1",
    ("CMP-SEP-SAT", "RS-75"): "SP-SEP-0503x1",
    ("CMP-INFLT-CLOG", "RS-75"): "SP-FLT-0501x1",
    ("CMP-OILFLT", "RS-75"): "SP-FLT-0502x1",
    ("CMP-MOTBRG", "RS-75"): "SP-BRG-0230x1",
    ("CMP-SHAFTSEAL", "RS-75"): "SP-SEAL-0042x1;SP-OIL-0550x1",
    ("CNV-ROLLER", "RC-1200"): "SP-BRG-0301x2",
    ("TST-SEAL", "PTS-2"): "SP-SEAL-0350x1",
}

LABOR_HOURS = {
    "CNC-SPBRG-WEAR": 10, "CNC-SPIMB": 1.5, "CNC-SPLUB": 2, "CNC-DBAR": 4, "CNC-COOL": 1,
    "CNC-SPMOT": 2, "CMP-COOLER-FOUL": 2, "CMP-TVALVE": 2, "CMP-SEP-SAT": 3,
    "CMP-INFLT-CLOG": 0.5, "CMP-OILFLT": 0.5, "CMP-MOTBRG": 8, "CMP-SHAFTSEAL": 6,
    "CMP-AIRLEAK": 4, "CNV-ROLLER": 3, "CNV-MISTRACK": 1, "TST-SEAL": 3, "TST-FLOWMETER": 2,
    "": 1,
}

# Preventive programs: model -> (interval in days, description, parts)
PM_PROGRAMS = {
    "VX-640": [(61, "Spindle lube and vibration route check.", "")],
    "HX-500": [(61, "Spindle lube and vibration route check.", "")],
    "RS-75": [
        (91, "2000-h service: intake filter and oil filter replaced, cooler blown out.",
         "SP-FLT-0501x1;SP-FLT-0502x1"),
        (182, "4000-h service: fluid change, oil filter and air/oil separator element replaced.",
         "SP-OIL-0550x1;SP-FLT-0502x1;SP-SEP-0503x1"),
    ],
    "RC-1200": [(91, "Quarterly conveyor inspection: belt tracking, rollers, guards.", "")],
    "PTS-2": [(182, "Semi-annual flowmeter calibration against reference meter.", "")],
}

TECHS = {
    "IND1": ["T-IND-03", "T-IND-07", "T-IND-11", "T-IND-14", "T-IND-19"],
    "MTY1": ["T-MTY-02", "T-MTY-05", "T-MTY-08"],
}

# --------------------------------------------------------------------------
# Spare parts (ERP export, one row per SKU and storeroom)
# --------------------------------------------------------------------------

# sku, description, supplier spellings (IND1, MTY1), fits models,
# (onhand, reorder) IND1, (onhand, reorder) MTY1, lead days, unit cost USD
PARTS = [
    ("SP-BRG-0114", "Spindle bearing set, matched pair, VX-640", ("Brightline Bearings", "Brightline Brgs"),
     "VX-640", (2, 1), None, 21, 1850.0),
    ("SP-BRG-0116", "Spindle bearing set, matched pair, HX-500", (None, "Brightline Bearing Co"),
     "HX-500", None, (0, 1), 28, 2240.0),
    ("SP-SEAL-0207", "Spindle labyrinth seal kit", ("Pellum Seal Co.", "Pellum Seals"),
     "VX-640;HX-500", (5, 2), (1, 1), 10, 145.0),
    ("SP-LUB-0402", "Spindle oil-air lube cartridge", ("Keystone MRO Supply", "Keystone MRO"),
     "VX-640;HX-500", (6, 2), (3, 1), 7, 62.0),
    ("SP-FLT-0405", "Lube line filter element", ("Keystone MRO Supply", "Keystone MRO"),
     "VX-640;HX-500", (4, 2), (0, 1), 7, 18.5),
    ("SP-SPRG-0031", "Drawbar disc spring stack", ("Varnell Machine Works", "varnell machine works"),
     "VX-640;HX-500", (1, 1), (2, 1), 30, 410.0),
    ("SP-FLT-0310", "Coolant filter cartridge 25 micron", ("Keystone MRO Supply", "Keystone MRO"),
     "VX-640;HX-500", (12, 6), (8, 4), 5, 34.0),
    ("SP-FAN-0044", "Spindle motor cooling fan", ("Ostrava Motor Works", "Ostrava Motor Works"),
     "VX-640;HX-500", (1, 1), (0, 1), 18, 275.0),
    ("SP-FLT-0501", "Compressor intake filter element", ("Tolland Air Systems", "Tolland Air Systems"),
     "RS-75", (4, 2), (2, 1), 6, 96.0),
    ("SP-FLT-0502", "Compressor oil filter element", ("Tolland Air Systems", "Tolland Air Systems"),
     "RS-75", (3, 2), (2, 1), 6, 54.0),
    ("SP-SEP-0503", "Air/oil separator element", ("Tolland Air Systems", "Tolland Air Systems"),
     "RS-75", (1, 1), (0, 1), 21, 388.0),
    ("SP-VLV-0520", "Thermostatic valve element kit", ("Tolland Air Systems", "Tolland Air Systems"),
     "RS-75", (1, 1), (1, 1), 14, 165.0),
    ("SP-SEAL-0042", "Airend shaft seal kit", ("Pellum Seal Co.", "Pellum Seal Co"),
     "RS-75", (2, 1), (1, 1), 12, 520.0),
    ("SP-BRG-0230", "Drive motor bearing set 6316/6314", ("Brightline Bearings", "Brightline Bearings"),
     "RS-75", (2, 1), (1, 1), 9, 310.0),
    ("SP-OIL-0550", "Compressor fluid, 20 l pail", ("Keystone MRO Supply", "Keystone MRO"),
     "RS-75", (6, 3), (4, 2), 4, 210.0),
    ("SP-BRG-0301", "Conveyor roller bearing 6205", ("Brightline Bearings", "Brightline Brgs"),
     "RC-1200", (10, 4), (6, 4), 5, 14.0),
    ("SP-SEAL-0350", "Test-loop pump mechanical seal 35 mm", ("Pellum Seal Co.", "Pellum Seals"),
     "PTS-2", (2, 1), (1, 1), 10, 230.0),
]

MXN_PER_USD = 18.0


def _messy_id(rng: random.Random, asset_id: str) -> str:
    """Return the asset ID the way a technician might have typed it."""
    prefix, num = asset_id.split("-")
    style = rng.random()
    if style < 0.04:
        return f"{prefix} {int(num)}"
    if style < 0.07:
        return f"{prefix.lower()}-{num}"
    if style < 0.09:
        return f"{asset_id} "
    return asset_id


def _fmt_date(d: date, site: str) -> str:
    """Format a date the way each site's CMMS export writes it."""
    if site == "MTY1":
        return d.strftime("%d/%m/%Y")
    return d.strftime("%m/%d/%Y") if d.day % 3 == 0 else d.isoformat()


def _site_of(area: str) -> str:
    return area.split("-")[0]


def write_assets(rng: random.Random) -> None:
    rows = [
        {"EquipmentID": "IND1", "Description": "Indianapolis plant", "Class": "SITE",
         "Site": "IND1", "ParentID": "", "Make": "", "Model": "", "SerialNo": "",
         "InstallDate": "", "Criticality": "A", "Status": "OPERATING"},
        {"EquipmentID": "MTY1", "Description": "Monterrey plant", "Class": "SITE",
         "Site": "MTY1", "ParentID": "", "Make": "", "Model": "", "SerialNo": "",
         "InstallDate": "", "Criticality": "A", "Status": "OPERATING"},
    ]
    for area_id, desc, site in AREAS:
        rows.append({"EquipmentID": area_id, "Description": desc, "Class": "AREA", "Site": site,
                     "ParentID": site, "Make": "", "Model": "", "SerialNo": "",
                     "InstallDate": "", "Criticality": "A", "Status": "OPERATING"})
    for eq_id, desc, cls, area, make, model, crit in EQUIPMENT:
        site = _site_of(area)
        install = date(2016 + rng.randint(0, 7), rng.randint(1, 12), rng.randint(1, 28))
        rows.append({
            "EquipmentID": eq_id, "Description": desc, "Class": cls, "Site": site,
            "ParentID": area, "Make": make + ("  " if rng.random() < 0.2 else ""),
            "Model": model, "SerialNo": f"{model.replace('-', '')}-{rng.randint(10000, 99999)}",
            "InstallDate": _fmt_date(install, site), "Criticality": crit, "Status": "OPERATING",
        })
    _write_csv(RAW / "cmms_assets.csv", rows)


def write_work_orders(rng: random.Random) -> None:
    by_model: dict[str, list[tuple[str, str]]] = {}
    for eq_id, _desc, _cls, area, _make, model, _crit in EQUIPMENT:
        by_model.setdefault(model, []).append((eq_id, _site_of(area)))
    crit_of = {e[0]: e[6] or "B" for e in EQUIPMENT}

    jobs: list[dict[str, object]] = []

    # Preventive work
    for model, programs in PM_PROGRAMS.items():
        for eq_id, site in by_model[model]:
            for interval, text, parts in programs:
                d = HISTORY_START + timedelta(days=rng.randint(0, interval - 1))
                while d <= HISTORY_END:
                    jobs.append({"asset": eq_id, "site": site, "type": "PM", "code": "",
                                 "reported": d, "completed": d, "text": text, "parts": parts,
                                 "hours": 1.0 if model != "RS-75" else 2.5, "prio": "3"})
                    d += timedelta(days=interval + rng.randint(-5, 5))

    # Corrective work (background)
    span = (BACKGROUND_END - HISTORY_START).days
    for model, counts in CORRECTIVE_COUNTS.items():
        for code, n in counts.items():
            for _ in range(n):
                eq_id, site = rng.choice(by_model[model])
                reported = HISTORY_START + timedelta(days=rng.randint(0, span))
                completed = reported + timedelta(days=rng.randint(0, 3))
                base = {"A": "2", "B": "3", "C": "4"}[crit_of[eq_id]]
                jobs.append({
                    "asset": eq_id, "site": site, "type": "CM", "code": code,
                    "reported": reported, "completed": completed,
                    "text": rng.choice(PROBLEM_TEXT[code]),
                    "parts": PARTS_USED.get((code, model), ""),
                    "hours": round(LABOR_HOURS[code] * rng.uniform(0.8, 1.4), 1),
                    "prio": base,
                })

    # Scripted recent corrective work
    for eq_id, code, completed, text, parts in SCRIPTED:
        site = "MTY1" if eq_id == "CMP-03" else "IND1"
        jobs.append({"asset": eq_id, "site": site, "type": "CM", "code": code,
                     "reported": completed - timedelta(days=1), "completed": completed,
                     "text": text, "parts": parts, "hours": LABOR_HOURS[code], "prio": "2"})

    jobs.sort(key=lambda j: (j["reported"], j["asset"]))
    rows = []
    for i, job in enumerate(jobs, start=1):
        site = str(job["site"])
        reported = job["reported"]
        completed = job["completed"]
        assert isinstance(reported, date) and isinstance(completed, date)
        status = "CLOSE" if completed < date(2026, 9, 1) else "COMP"
        if job["type"] == "PM" and completed > date(2026, 9, 20):
            status = "INPRG"
        rows.append({
            "WONum": f"{site}-{reported:%y}{i:04d}",
            "Equipment": _messy_id(rng, str(job["asset"])),
            "WOType": job["type"],
            "Priority": job["prio"],
            "Status": status,
            "Reported": _fmt_date(reported, site),
            "Completed": "" if status == "INPRG" else _fmt_date(completed, site),
            "FailureCode": job["code"],
            "ProblemDesc": job["text"],
            "LaborHrs": "" if rng.random() < 0.05 else job["hours"],
            "PartsUsed": job["parts"],
            "Technician": rng.choice(TECHS[site]),
            "DowntimeHrs": "" if job["type"] == "PM" else round(float(job["hours"]) * rng.uniform(1.0, 3.0), 1),
        })
    # The CMMS export repeats a few rows when a work order spans two report pages.
    for idx in rng.sample(range(len(rows)), 3):
        rows.insert(idx + 1, dict(rows[idx]))
    _write_csv(RAW / "cmms_work_orders.csv", rows)


def write_spare_parts() -> None:
    rows = []
    for sku, desc, suppliers, fits, ind1, mty1, lead, cost in PARTS:
        for storeroom, stock, supplier, site in (
            ("IND1-STORES", ind1, suppliers[0], "IND1"),
            ("MTY1-STORES", mty1, suppliers[1], "MTY1"),
        ):
            if stock is None:
                continue
            onhand, reorder = stock
            mxn = site == "MTY1"
            rows.append({
                "ItemNo": sku, "ItemDesc": desc, "Storeroom": storeroom,
                "OnHand": onhand, "ReorderPt": reorder,
                "LeadTimeDays": lead + (7 if mxn else 0),
                "UnitCost": round(cost * MXN_PER_USD, 2) if mxn else cost,
                "Currency": "MXN" if mxn else "USD",
                "BinLoc": f"{'A' if sku.startswith('SP-BRG') else 'B'}{len(rows) % 9 + 1}-{len(rows) % 5 + 1}",
                "Supplier": supplier, "FitsModels": fits,
            })
    _write_csv(RAW / "erp_spare_parts.csv", rows)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {path.relative_to(ROOT)} ({len(rows)} rows)")


def main() -> None:
    rng = random.Random(SEED)
    write_assets(rng)
    write_work_orders(rng)
    write_spare_parts()


if __name__ == "__main__":
    main()

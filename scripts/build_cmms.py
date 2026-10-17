"""Convert data/raw CSV exports into build/cmms for machina's GenericCmmsConnector.

Run: python scripts/build_cmms.py   (writes docs/data_load_report.txt)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from corvane_pm.config import CMMS_DIR, CONFIG_DIR, DOCS_DIR, RAW_DIR  # noqa: E402
from corvane_pm.data_loader import build_cmms_dir  # noqa: E402


def main() -> None:
    report = build_cmms_dir(RAW_DIR, CONFIG_DIR, CMMS_DIR)
    text = report.render()
    print(text)
    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "data_load_report.txt").write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

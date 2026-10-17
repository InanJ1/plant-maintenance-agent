"""Score the Corvane workflow and machina's built-in workflow on eval/alarms.yaml.

Run: python scripts/run_eval.py   (writes docs/eval_results.md and docs/eval_results.json)
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from corvane_pm.config import CMMS_DIR, CONFIG_DIR, DOCS_DIR, EVAL_FILE  # noqa: E402
from corvane_pm.evaluation import (  # noqa: E402
    load_alarms,
    render_markdown,
    run_baseline,
    run_corvane,
    score,
)


async def main() -> None:
    alarms = load_alarms(EVAL_FILE)
    corvane = score(alarms, await run_corvane(alarms, cmms_dir=CMMS_DIR, config_dir=CONFIG_DIR))
    baseline = score(alarms, await run_baseline(alarms, cmms_dir=CMMS_DIR))
    md = render_markdown(corvane, baseline)
    (DOCS_DIR / "eval_results.md").write_text(md, encoding="utf-8")
    (DOCS_DIR / "eval_results.json").write_text(
        json.dumps({"corvane": corvane, "baseline": baseline}, indent=2, default=str) + "\n",
        encoding="utf-8")
    print(md.split("## Per alarm")[0])
    print("Misses:", [r["alarm_id"] for r in corvane["rows"] if not r["ok"]["all_three"]])


if __name__ == "__main__":
    from machina.observability.logging import configure_logging

    configure_logging(level="WARNING")
    asyncio.run(main())

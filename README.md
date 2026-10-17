# Corvane plant-maintenance agent (on machina)

I deployed [machina](https://github.com/LGDiMaggio/machina), an open-source Python framework
for industrial-maintenance AI agents, for Corvane Industrial, a fictional pump and gearbox
maker with plants in Indianapolis (IND1) and Monterrey (MTY1). machina is a pinned dependency
(`machina-ai==0.4.0`). This repo holds only my code, Corvane's config and synthetic data.

## The Corvane scenario

Unplanned downtime on CNC spindles and air compressors. The fixes live in technicians' heads
and in PDF manuals. When an alarm fires, a planner works out the cause, checks the storeroom,
sets a priority and writes the work order by hand.

## Results

| What | Result | Source |
| --- | --- | --- |
| Upstream tests (installed wheel) | 422 passed | `docs/upstream_tests.txt` |
| Upstream alarm example | SUCCESS, 6 steps, writes sandboxed | `docs/upstream_alarm_example.txt` |
| Failure mode correct, 20 alarms | 17/20 (built-in workflow: 14/20) | `docs/eval_results.md` |
| Priority correct | 20/20 (built-in: 6/20, always "medium") | `docs/eval_results.md` |
| Required parts correct (SKU and qty) | 18/20 (built-in: 4/20, puts no parts on the WO) | `docs/eval_results.md` |
| All three correct | 17/20 (built-in: 0/20) | `docs/eval_results.md` |
| Workflow time per alarm | 24 to 94 ms, no LLM call | `docs/alarm_demo.txt` |
| Technician Q&A, qwen2.5:3b on CPU | QA_RESULT | `docs/qa_transcripts.md` |
| My tests | 28 passed | `python -m pytest` |

The eval numbers come from `python scripts/run_eval.py`. The labels and the rules were written
by the same person (me), so 20/20 on priority shows the policy is wired correctly, not that the
policy is right. The three misses are real limits of rule-based diagnosis:

- ALM-2610-005: hot spindle bearing, no other signal. Bearing wear and lube starvation both
  fit; history says bearing wear is more common on the VX-640, but this time it was the lube filter.
- ALM-2610-011: high discharge temperature on CMP-02, no cooler or oil temperatures on the
  network. Picked cooler fouling (most common); it was the thermostatic valve.
- ALM-2610-016: a failed temperature sensor read 131 °C. The catalog has no sensor-fault mode,
  so the workflow diagnosed cooler fouling. A plausibility check (a big jump with no
  corroborating signal) is the next rule I would add.

## Quickstart

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
copy .env.example .env                       # shared Ollama defaults
.venv\Scripts\python scripts\generate_data.py    # seeded CSV exports (seed 42), already committed
.venv\Scripts\python scripts\build_cmms.py       # CSV -> build/cmms/*.json + docs/data_load_report.txt
$env:PYTHONUTF8=1
.venv\Scripts\python scripts\run_alarm_demo.py   # 4 alarms, scripted planner answers
.venv\Scripts\python scripts\run_alarm_demo.py --interactive --alarms ALM-2610-012
.venv\Scripts\python scripts\run_eval.py         # docs/eval_results.md
.venv\Scripts\python scripts\run_qa.py           # needs Ollama; docs/qa_transcripts.md
.venv\Scripts\python -m pytest
```

`PYTHONUTF8=1` is needed on a Windows console: machina's built-in notification text has an
emoji that the cp1252 console cannot print.

## How it works

1. **Data adapter** (`corvane_pm/data_loader.py`). Corvane's CMMS and ERP export CSV. The
   loader turns them into the JSON directory that machina's `GenericCmmsConnector` reads. It
   fixes hand-typed equipment IDs ("CNC 4"), parses IND1 month-first and MTY1 day-first dates,
   drops duplicate rows, maps status and priority codes, canonicalizes supplier typos, converts
   MTY1 costs from MXN, and links parts to assets by machine model and storeroom site. Every
   record goes through machina's pydantic models. I chose the JSON connector because in 0.4.0
   it is the only file-based connector with spare parts and maintenance history
   (`ExcelCsvConnector` has neither).
2. **Workflow** (`corvane_pm/workflow.py`, `services.py`). Ten steps on machina's
   `WorkflowEngine`: diagnose with machina's `FailureAnalyzer` scoped to the asset's own failure
   modes (out-of-limit related readings count as extra symptoms, ties go to the most frequent
   cause in that model's history), read history and stock through the connector, look up the
   repair kit, apply the planners' priority policy (criticality x severity, past-trip and
   repeat-failure escalation), draft with machina's `WorkOrderFactory`, then ask a planner.
   Submit and notify are guarded on the approval and intercepted by sandbox mode.
3. **Q&A agent** (`corvane_pm/qa_agent.py`, `docs.py`, `llm.py`). machina's `Agent` over the
   CMMS data and seven synthetic manuals and SOPs, with Chroma plus BM25 retrieval. Embeddings
   use `nomic-embed-text` on the shared Ollama, and answers use `qwen2.5:3b`.

## What's upstream and what I built

Upstream (machina-ai 0.4.0, unmodified): domain model, `FailureAnalyzer`, `WorkOrderFactory`,
`WorkflowEngine` and sandbox gating, `GenericCmmsConnector`, `DocumentStoreConnector` (chunking,
Chroma, BM25), `Agent` (entity resolution, tool loop, citations), LiteLLM provider, and the
built-in `alarm_to_workorder` workflow I use as the baseline.

I built (all new files, no upstream file changed):

- `corvane_pm/data_loader.py`: CSV exports to machina's JSON layout, with a load report
- `corvane_pm/services.py`: asset-scoped diagnosis, repair-kit parts plan, priority policy, draft completion, approval step
- `corvane_pm/workflow.py`: the Corvane workflow, runtime wiring, result summary
- `corvane_pm/approvals.py`: console, scripted and no-approver modes
- `corvane_pm/llm.py`: `LLMProvider` subclass for `LLM_BASE_URL`/`LLM_API_KEY`, Ollama embeddings
- `corvane_pm/docs.py`: `DocumentStoreConnector` subclass for family-scoped search and Ollama embeddings
- `corvane_pm/qa_agent.py`, `corvane_pm/evaluation.py`, `corvane_pm/config.py`
- `config/*.yaml`: failure-mode catalog, repair kits, alarm limits, priority policy, data mapping
- `data/raw/*.csv` (from `scripts/generate_data.py`), `data/manuals/*.md`, `eval/alarms.yaml`
- `scripts/*.py`, `tests/*.py`, `docs/*`

## Limitations

- All data is synthetic, and the eval labels come from the same author as the rules.
- `corvane_pm/docs.py` overrides machina's internal `_load_embedding_function` hook and ranks the
  whole corpus before filtering by family. Both are fine for 7 manuals and a pinned version, but
  not for a large document store.
- machina 0.4.0 quirks I worked around: the prompt shows only the first 10 work orders in file
  order and no dates (the loader sorts newest first and puts the date in the description); the
  JSON connector drops `Asset.aliases` and `install_date` (kept in metadata); write detection
  by substring would gate `assess_priority` ("set"), so every step sets `is_write`.
- Only sandbox mode is exposed. A test runs the live path on a temporary copy of the CMMS files.
- Q&A on CPU is slow: a qwen2.5:7b question did not finish in 900 s while other jobs shared the
  Ollama server, so the recorded run uses qwen2.5:3b.
- No UI. machina has an MCP server, which I did not deploy.

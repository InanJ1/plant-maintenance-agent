# STATUS: plant-maintenance-agent (Corvane on machina-ai 0.4.0)

## Progress (for resume)
- All stages done except where noted under Open issues. Commits: 770bf0a, 2e8cf7b, 291a35a (+ Q&A commit).

## Stages
| Stage | Status | Evidence |
| --- | --- | --- |
| Cloned | yes | `fde-projects/_upstream/machina` (Apache-2.0, tag v0.4.0 = bac3027). Source skimmed: no install hooks, no telemetry, no obfuscation; network calls only in connectors. |
| Runnable | yes | 422 upstream unit tests passed against the installed PyPI wheel (`docs/upstream_tests.txt`); upstream `examples/alarm_to_workorder` SUCCESS (`docs/upstream_alarm_example.txt`). Installed wheel is identical to the tag's `src/` (diff ignoring CRLF). |
| Customized | yes | Corvane data adapter, 10-step workflow with approval gate, 20-alarm eval, Q&A agent over 7 manuals (see README). |
| Tested | yes | `python -m pytest`: 28 passed (loader, workflow wiring incl. live write only after approval on a temp copy, eval numbers locked, family-scoped doc search). |
| Published | no | Local git only, no remote. |

## Commands to run the demo
```powershell
cd fde-projects\plant-maintenance-agent
.venv\Scripts\python -m pip install -e ".[dev]"
copy .env.example .env
.venv\Scripts\python scripts\build_cmms.py
$env:PYTHONUTF8=1
.venv\Scripts\python scripts\run_alarm_demo.py              # or --interactive
.venv\Scripts\python scripts\run_eval.py
.venv\Scripts\python scripts\run_qa.py                      # needs shared Ollama
.venv\Scripts\python -m pytest
```

## Files added (no upstream file changed; machina is a pinned dependency)
- `corvane_pm/`: data_loader.py, services.py, workflow.py, approvals.py, evaluation.py, docs.py, llm.py, qa_agent.py, config.py
- `config/`: failure_modes.yaml, repair_kits.yaml, alarm_parameters.yaml, priority_policy.yaml, data_mapping.yaml
- `data/raw/*.csv` (seeded by `scripts/generate_data.py`, seed 42), `data/manuals/*.md` (7 synthetic manuals/SOPs), `eval/alarms.yaml`
- `scripts/`: generate_data.py, build_cmms.py, run_alarm_demo.py, run_eval.py, run_qa.py
- `tests/`: conftest.py, test_data_loader.py, test_workflow.py, test_eval.py, test_docs.py
- `docs/`: upstream_tests.txt, upstream_alarm_example.txt, data_load_report.txt, alarm_demo.txt, eval_results.md/.json, qa_transcripts.md, qa_results.json
- README.md, NOTICE, LICENSE (upstream Apache-2.0 text), pyproject.toml, .env.example, .gitignore

## Portfolio numbers (each from a run I did)
- Corvane workflow on 20 synthetic alarms: failure mode 17/20, priority 20/20, parts 18/20, all three 17/20. machina's built-in workflow on the same data: 14/20, 6/20, 4/20, 0/20. Source: `docs/eval_results.md`, `python scripts/run_eval.py`. Caveat: labels and rules have the same author; misses ALM-2610-005, -011, -016 are explained in the README.
- Alarm to drafted work order in 24 to 94 ms with no LLM call, nothing written without planner approval, writes sandboxed. Source: `docs/alarm_demo.txt`.
- Data adapter on messy exports: 223 work-order rows to 220 (3 duplicates dropped), 25 equipment IDs and 122 dates normalized, 16 MXN costs converted, 10 supplier typos fixed. Source: `docs/data_load_report.txt`, `python scripts/build_cmms.py`.
- Upstream proof: 422 upstream tests passed. Source: `docs/upstream_tests.txt`.
- Technician Q&A (qwen2.5:3b, CPU): QA_RESULT. Source: `docs/qa_transcripts.md`, `python scripts/run_qa.py`.

## Open issues and blockers
- Q&A latency: on the shared CPU Ollama, qwen2.5:7b did not finish one question in 900 s (index build itself took 80 s), so the recorded run uses qwen2.5:3b with 4 questions.
- Upstream example's first run downloaded Chroma's default ONNX embedder (79.3 MB) into `C:\Users\inanj\.cache\chroma`, because the example builds a DocumentStoreConnector without an embedder. My deployment does not need it (it uses nomic-embed-text on Ollama).
- On a Windows console, machina's notification step fails with UnicodeEncodeError unless `PYTHONUTF8=1` is set (emoji in the log line).
- `[docs-rag]` extra installed as its parts minus `langchain-huggingface` (avoids torch); `corvane_pm/docs.py` overrides an internal machina hook, which is OK while machina stays pinned at 0.4.0.
- No UI or server deployed (machina's MCP server not used), so no screenshot.

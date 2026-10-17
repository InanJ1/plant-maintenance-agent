# STATUS

## Progress (for resume)
- Done: upstream cloned at _upstream/machina (tag v0.4.0 checked out), source skimmed (no hooks, no telemetry).
- Done: venv with machina-ai==0.4.0 (+litellm, excel, examples, docs-rag-hybrid); docs-rag deps installing without langchain-huggingface (avoids torch).
- Done: config/*.yaml, data/manuals/*.md, scripts/generate_data.py (raw CSVs generated), corvane_pm/{data_loader,services,approvals,workflow,config,llm,docs,qa_agent}.py, eval/alarms.yaml.
- Next: build_cmms script, upstream tests + example proof, demo, eval, Q&A, tests, README/NOTICE, git.
- Done: upstream proof: 422 upstream unit tests passed (docs/upstream_tests.txt); upstream alarm example SUCCESS (docs/upstream_alarm_example.txt). Wheel == tag source.
- Done: build_cmms (docs/data_load_report.txt), Corvane workflow demo (docs/alarm_demo.txt), eval: Corvane 17/20 FM, 20/20 priority, 18/20 parts vs upstream built-in 14/20, 6/20, 4/20 (docs/eval_results.md).
- Next: Q&A run (docs/qa_*), pytest suite, README/NOTICE/.env.example/pyproject, git commit.

"""Ask the technician Q&A agent a fixed set of questions and record the answers.

    python scripts/run_qa.py              # all questions -> docs/qa_transcripts.md, docs/qa_results.json
    python scripts/run_qa.py --only 1 3   # a subset (printed only, files not written)

Needs the shared Ollama (LLM_BASE_URL, LLM_MODEL, EMBED_MODEL in .env or the environment).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from corvane_pm.config import CMMS_DIR, DOCS_DIR, MANUALS_DIR, load_settings  # noqa: E402
from corvane_pm.qa_agent import build_qa_agent  # noqa: E402

QUESTIONS = [
    "CNC-04 has a spindle vibration alarm. What is the bearing replacement procedure "
    "and which parts do I need?",
    "What are the discharge temperature limits on CMP-03, and what should I check first "
    "when it runs hot?",
    "Do we have spindle bearing sets in stock for CNC-07?",
    "When was the air/oil separator element last replaced on CMP-01?",
    "What lockout steps do I follow before opening the cooler on CMP-03?",
    "What is the warranty period for the spindle on CNC-06?",
]


async def main(only: list[int] | None) -> None:
    settings = load_settings()
    agent, tracer = build_qa_agent(settings, cmms_dir=CMMS_DIR, manuals_dir=MANUALS_DIR)
    t0 = time.perf_counter()
    await agent.start()
    startup_s = time.perf_counter() - t0
    docs_conn = next(c for c in agent._registry.all().values() if hasattr(c, "search_documents"))
    health = await docs_conn.health_check()
    print(f"model={settings.model} embed={settings.embed_model} startup={startup_s:.1f}s "
          f"docs={health.details}")
    results = []
    picked = [(i, q) for i, q in enumerate(QUESTIONS, 1) if not only or i in only]
    try:
        for i, question in picked:
            before = len(tracer.entries)
            start = time.perf_counter()
            error = None
            try:
                resp = await agent.handle_message_full(question, chat_id=f"qa-{i}")
                text, citations = resp.text, [c.model_dump() for c in resp.citations]
                fallback, completeness = resp.is_fallback, resp.completeness
            except Exception as exc:  # recorded, not hidden
                text, citations, fallback, completeness = "", [], None, None
                error = f"{type(exc).__name__}: {exc}"
            latency = time.perf_counter() - start
            calls = [e for e in tracer.entries[before:] if e.action == "llm_call"]
            row = {
                "n": i, "question": question, "answer": text, "error": error,
                "citations": [{"source": c["source"], "page": c["page"]} for c in citations],
                "latency_s": round(latency, 1), "llm_calls": len(calls),
                "prompt_tokens": sum(e.prompt_tokens for e in calls),
                "completion_tokens": sum(e.completion_tokens for e in calls),
                "is_fallback": fallback, "completeness": completeness,
            }
            results.append(row)
            print(f"\n[{i}] {question}\n--- {row['latency_s']}s, {row['llm_calls']} LLM calls, "
                  f"{row['prompt_tokens']}+{row['completion_tokens']} tokens, error={error}\n{text}\n"
                  f"sources: {row['citations']}")
    finally:
        await agent.stop()
    if only:
        return
    meta = {"model": settings.model, "embed_model": settings.embed_model,
            "base_url": settings.base_url, "startup_s": round(startup_s, 1),
            "docs_index": health.details}
    (DOCS_DIR / "qa_results.json").write_text(
        json.dumps({"meta": meta, "results": results}, indent=2) + "\n", encoding="utf-8")
    (DOCS_DIR / "qa_transcripts.md").write_text(render(meta, results), encoding="utf-8")


def render(meta: dict, results: list[dict]) -> str:
    lat = sorted(r["latency_s"] for r in results)
    lines = [
        "# Technician Q&A transcripts",
        "",
        f"Produced by `python scripts/run_qa.py`. Model `{meta['model']}` and embeddings "
        f"`{meta['embed_model']}` on the shared local Ollama (CPU only, shared with other jobs). "
        f"Agent startup (index build) {meta['startup_s']} s. Docs index: {meta['docs_index']}.",
        "",
        f"Latency per question: median {lat[len(lat) // 2]} s, min {lat[0]} s, max {lat[-1]} s.",
        "",
    ]
    for r in results:
        src = ", ".join(sorted({c["source"] for c in r["citations"]})) or "none cited"
        lines += [
            f"## Q{r['n']}. {r['question']}", "",
            f"Latency {r['latency_s']} s, {r['llm_calls']} LLM call(s), "
            f"{r['prompt_tokens']} prompt + {r['completion_tokens']} completion tokens. "
            f"Cited sources: {src}.", "",
        ]
        if r["error"]:
            lines += [f"Error: `{r['error']}`", ""]
        lines += ["> " + line if line else ">" for line in (r["answer"] or "(no answer)").splitlines()]
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", nargs="+", type=int)
    args = parser.parse_args()
    from machina.observability.logging import configure_logging

    configure_logging(level="WARNING")
    asyncio.run(main(args.only))

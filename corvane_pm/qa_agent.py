"""Technician Q&A agent: machina's Agent over Corvane's CMMS data and manuals."""

from __future__ import annotations

from typing import TYPE_CHECKING

from machina import Agent, Plant
from machina.connectors.cmms import GenericCmmsConnector
from machina.observability.tracing import ActionTracer

from corvane_pm.docs import CorvaneDocStore
from corvane_pm.llm import OpenAICompatEmbeddings, OpenAICompatProvider

if TYPE_CHECKING:
    from pathlib import Path

    from corvane_pm.config import LLMSettings


def build_qa_agent(
    settings: LLMSettings, *, cmms_dir: Path, manuals_dir: Path
) -> tuple[Agent, ActionTracer]:
    """Return the agent and the tracer that records its LLM calls.

    Sandbox mode and the confirmation gate stay on: the agent answers
    questions, and any work-order write it proposes is withheld.
    """
    tracer = ActionTracer()
    agent = Agent(
        name="Corvane technician assistant",
        description="Answers maintenance questions for Corvane's IND1 and MTY1 plants",
        plant=Plant(name="Corvane Industrial (IND1 Indianapolis, MTY1 Monterrey)"),
        connectors=[
            GenericCmmsConnector(data_dir=cmms_dir),
            CorvaneDocStore(paths=[manuals_dir], embeddings=OpenAICompatEmbeddings(settings)),
        ],
        llm=OpenAICompatProvider(settings, tracer=tracer),
        sandbox=True,
        confirmations=True,
    )
    return agent, tracer

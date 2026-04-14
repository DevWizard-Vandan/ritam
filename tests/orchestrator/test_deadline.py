"""Tests for the as_completed deadline loop in MarketOrchestrator."""
from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
import concurrent.futures
from unittest.mock import MagicMock

import pytest

from src.agents.base import AgentSignal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_agent(name: str, delay: float) -> MagicMock:
    """Return a mock agent whose run() sleeps `delay` seconds then returns an AgentSignal."""
    agent = MagicMock()
    agent.name = name

    def _run():
        time.sleep(delay)
        return AgentSignal(
            agent_name=name,
            signal=1,
            confidence=0.5,
            reasoning="mock",
            raw_data={},
        )

    agent.run = _run
    return agent


def _run_deadline_loop(agents: list, deadline: float) -> tuple[list[AgentSignal], list[str]]:
    """
    Replicate the as_completed deadline loop from MarketOrchestrator.run_cycle().
    Returns (collected_signals, cancelled_agent_names).
    """
    agent_signals: list[AgentSignal] = []
    cancelled: list[str] = []

    with ThreadPoolExecutor(max_workers=len(agents)) as executor:
        futures: dict[Future, object] = {executor.submit(a.run): a for a in agents}
        collected: set[Future] = set()

        try:
            for future in as_completed(futures, timeout=deadline):
                agent = futures[future]
                collected.add(future)
                try:
                    agent_signals.append(future.result())
                except Exception:
                    pass
        except concurrent.futures.TimeoutError:
            for future, agent in futures.items():
                if future in collected:
                    continue
                if future.done():
                    collected.add(future)
                    try:
                        agent_signals.append(future.result())
                    except Exception:
                        pass
                else:
                    future.cancel()
                    cancelled.append(agent.name)

    return agent_signals, cancelled


# ---------------------------------------------------------------------------
# Test 1 — slow agent doesn't block fast agents
# ---------------------------------------------------------------------------

def test_slow_agent_does_not_block_fast_agents():
    """
    7 fast agents (0.1 s) + 1 slow agent (35 s).
    With a 2-second deadline, all 7 fast signals must be collected and
    the slow agent must be cancelled.
    """
    fast_agents = [_make_agent(f"Fast{i}", 0.1) for i in range(7)]
    slow_agent = _make_agent("SlowGlobalMarket", 35)
    all_agents = fast_agents + [slow_agent]

    signals, cancelled = _run_deadline_loop(all_agents, deadline=2.0)

    assert len(signals) == 7, (
        f"Expected 7 signals from fast agents, got {len(signals)}: "
        f"{[s.agent_name for s in signals]}"
    )
    assert "SlowGlobalMarket" in cancelled, (
        "Slow agent should have been cancelled"
    )
    fast_names = {s.agent_name for s in signals}
    for i in range(7):
        assert f"Fast{i}" in fast_names


# ---------------------------------------------------------------------------
# Test 2 — boundary recovery
# ---------------------------------------------------------------------------

def test_boundary_agent_is_recovered_after_timeout():
    """
    One agent completes at deadline - 0.05 s (just before boundary).
    It must appear in agent_signals even though the timeout fires shortly after.
    """
    deadline = 1.0
    # Agent finishes at ~deadline - 0.05 s → should be recovered
    boundary_agent = _make_agent("BoundaryAgent", deadline - 0.05)
    # Give the second agent plenty of time so it doesn't interfere
    slow_agent = _make_agent("SlowAgent", 30)

    signals, cancelled = _run_deadline_loop([boundary_agent, slow_agent], deadline=deadline)

    recovered_names = {s.agent_name for s in signals}
    assert "BoundaryAgent" in recovered_names, (
        "BoundaryAgent finished just before deadline and should be in signals"
    )
    assert "SlowAgent" in cancelled


# ---------------------------------------------------------------------------
# Test 3 — all agents fast
# ---------------------------------------------------------------------------

def test_all_fast_agents_collected_no_cancellations():
    """
    All 8 agents complete in 0.05 s, well within a 2-second deadline.
    All 8 results must be present and no agent should be cancelled.
    """
    agents = [_make_agent(f"Agent{i}", 0.05) for i in range(8)]

    signals, cancelled = _run_deadline_loop(agents, deadline=2.0)

    assert len(signals) == 8, (
        f"Expected 8 signals, got {len(signals)}: {[s.agent_name for s in signals]}"
    )
    assert cancelled == [], f"No agents should be cancelled, got: {cancelled}"
    collected_names = {s.agent_name for s in signals}
    for i in range(8):
        assert f"Agent{i}" in collected_names

"""Agent registry — add new agents here, orchestrator picks them up."""
from src.agents.base import AgentBase
REGISTERED_AGENTS: list[type[AgentBase]] = []
# Agents will be imported and appended here as they are built in L2
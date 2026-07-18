"""Backward-compatible imports for callers using the old module path."""

from backend.agent.service import build_messages, get_agent, run_agent

__all__ = ["build_messages", "get_agent", "run_agent"]

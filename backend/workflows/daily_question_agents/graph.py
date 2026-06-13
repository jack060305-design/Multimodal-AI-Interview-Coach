"""
LangGraph multi-agent workflow for daily question generation.

Planner → Researcher (no LLM) → Generator → Critic → [optional revision loop] → Finalize

Cost profile (gpt-4o-mini, 4 roles × 3 questions):
  ~1 planner + 4 generator + 1 critic = 6 LLM calls/day
  + up to 4 generator + 1 critic on revision = 11 max
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from workflows.daily_question_agents.critic import critic_node
from workflows.daily_question_agents.finalize import finalize_node
from workflows.daily_question_agents.generator import generator_node
from workflows.daily_question_agents.planner import planner_node
from workflows.daily_question_agents.researcher import researcher_node
from workflows.daily_question_agents.routing import route_after_critic
from workflows.daily_question_agents.state import DailyQuestionState


def _increment_revision(state: DailyQuestionState) -> DailyQuestionState:
    state = dict(state)
    state["revision_round"] = int(state.get("revision_round", 0)) + 1
    return state


def build_daily_question_graph():
    g = StateGraph(DailyQuestionState)
    g.add_node("planner", planner_node)
    g.add_node("researcher", researcher_node)
    g.add_node("generator", generator_node)
    g.add_node("critic", critic_node)
    g.add_node("finalize", finalize_node)
    g.add_node("increment_revision", _increment_revision)

    g.set_entry_point("planner")
    g.add_edge("planner", "researcher")
    g.add_edge("researcher", "generator")
    g.add_edge("generator", "critic")
    g.add_conditional_edges(
        "critic",
        route_after_critic,
        {"generator": "increment_revision", "finalize": "finalize"},
    )
    g.add_edge("increment_revision", "generator")
    g.add_edge("finalize", END)
    return g.compile()


DailyQuestionAgentGraph = build_daily_question_graph()

"""
LangGraph definition mirroring Friday's 5-agent conditional routing.
Used for visualization / optional full-graph invoke; turns use orchestrator.run_turn.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from workflows.interview_agents.clarifier import clarifier_node
from workflows.interview_agents.coach import coach_node
from workflows.interview_agents.followup import followup_node
from workflows.interview_agents.grader import grader_node
from workflows.interview_agents.interviewer import interviewer_node
from workflows.interview_agents.routing import route_after_followup, route_after_grader
from workflows.interview_agents.state import InterviewState


def route_after_coach(state: InterviewState) -> str:
    if state.get("session_complete"):
        return END
    return "interviewer"


def build_interview_graph():
    g = StateGraph(InterviewState)
    g.add_node("interviewer", interviewer_node)
    g.add_node("grader", grader_node)
    g.add_node("clarifier", clarifier_node)
    g.add_node("followup", followup_node)
    g.add_node("coach", coach_node)

    g.set_entry_point("interviewer")
    g.add_edge("interviewer", "grader")
    g.add_conditional_edges(
        "grader",
        route_after_grader,
        {"clarifier": "clarifier", "followup": "followup", "coach": "coach"},
    )
    g.add_edge("clarifier", "coach")
    g.add_conditional_edges(
        "followup",
        route_after_followup,
        {"interviewer": "interviewer", "coach": "coach"},
    )
    g.add_conditional_edges(
        "coach",
        route_after_coach,
        {"interviewer": "interviewer", END: END},
    )
    return g.compile()


InterviewAgentGraph = build_interview_graph()

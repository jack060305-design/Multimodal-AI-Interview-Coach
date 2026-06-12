import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from rubrics.bank_rubrics import BANK_RUBRICS
from rubrics.registry import build_rubric_index
from schemas import Role, RubricCriterion, RubricDocument


_BASE_RUBRICS: list[RubricDocument] = [
    RubricDocument(
        role=Role.SWE_INTERN,
        question_id="react_useeffect_001",
        question="Explain how React useEffect works and when you would use it.",
        ideal_answer=(
            "useEffect runs side effects after render. It accepts a callback and optional "
            "dependency array. Empty deps run once on mount; listed deps re-run when they change. "
            "Cleanup functions prevent leaks (subscriptions, timers). Common uses: data fetching, "
            "DOM sync, subscriptions. Watch stale closures when deps are omitted incorrectly."
        ),
        evaluation_guidelines=(
            "Score strictly on React fundamentals. Penalize confusion between useEffect and useLayoutEffect "
            "only if candidate claims they are identical. Require mention of dependency array for full credit."
        ),
        rubric=[
            RubricCriterion(
                criterion="Understanding of side effects in React",
                weight=20,
                levels={
                    "0": "Cannot explain or confuses with lifecycle methods incorrectly",
                    "5": "Mentions side effects vaguely",
                    "8": "Explains side effects with one valid example",
                    "10": "Clear explanation with multiple examples and pitfalls",
                },
            ),
            RubricCriterion(
                criterion="Dependency array behavior",
                weight=30,
                levels={
                    "0": "No mention or completely wrong",
                    "5": "Mentions deps but incorrect behavior",
                    "8": "Correct basic behavior (mount vs update)",
                    "10": "Explains empty deps, dep list, and stale closure risk",
                },
            ),
            RubricCriterion(
                criterion="Cleanup function",
                weight=25,
                levels={
                    "0": "Not mentioned",
                    "5": "Mentioned without purpose",
                    "8": "Explains cleanup with one example",
                    "10": "Explains why cleanup matters with concrete leak example",
                },
            ),
            RubricCriterion(
                criterion="Practical use cases",
                weight=25,
                levels={
                    "0": "No use cases",
                    "5": "One generic use case",
                    "8": "Two relevant use cases",
                    "10": "Multiple use cases with when NOT to use useEffect",
                },
            ),
        ],
    ),
    RubricDocument(
        role=Role.DATA_ANALYST,
        question_id="sql_window_functions_001",
        question="What are SQL window functions and give an example use case?",
        ideal_answer=(
            "Window functions compute aggregates over a row set related to the current row without collapsing "
            "rows. Syntax: FUNCTION() OVER (PARTITION BY ... ORDER BY ...). Examples: ROW_NUMBER, RANK, "
            "LAG/LEAD, running totals. Use case: ranking sales per region, cohort retention, moving averages."
        ),
        evaluation_guidelines=(
            "Candidate must distinguish window functions from GROUP BY. Example must include OVER clause."
        ),
        rubric=[
            RubricCriterion(
                criterion="Definition vs GROUP BY",
                weight=30,
                levels={
                    "0": "Confuses with GROUP BY",
                    "5": "Partial distinction",
                    "8": "Clear distinction",
                    "10": "Clear distinction with why row retention matters",
                },
            ),
            RubricCriterion(
                criterion="Syntax (OVER / PARTITION / ORDER)",
                weight=25,
                levels={
                    "0": "No syntax",
                    "5": "Mentions OVER only",
                    "8": "OVER with PARTITION or ORDER",
                    "10": "Full syntax with frame awareness",
                },
            ),
            RubricCriterion(
                criterion="Named functions",
                weight=20,
                levels={
                    "0": "None named",
                    "5": "One function",
                    "8": "Two to three functions",
                    "10": "Several functions with purpose",
                },
            ),
            RubricCriterion(
                criterion="Real-world example",
                weight=25,
                levels={
                    "0": "No example",
                    "5": "Vague example",
                    "8": "Concrete business example",
                    "10": "Concrete example with SQL snippet or pseudo-SQL",
                },
            ),
        ],
    ),
    RubricDocument(
        role=Role.FINANCE_ANALYST,
        question_id="dcf_basics_001",
        question="Walk me through a basic DCF valuation approach.",
        ideal_answer=(
            "Project free cash flows, discount at WACC, sum PV of FCF, add terminal value "
            "(Gordon growth or exit multiple), enterprise value minus net debt = equity value. "
            "Discuss assumptions: growth, margins, capex, working capital, discount rate."
        ),
        evaluation_guidelines="Require FCF, discount rate, and terminal value for advanced scores.",
        rubric=[
            RubricCriterion(
                criterion="FCF projection",
                weight=30,
                levels={
                    "0": "Missing",
                    "5": "Mentioned only",
                    "8": "Explains components",
                    "10": "Full FCF build intuition",
                },
            ),
            RubricCriterion(
                criterion="Discount rate (WACC)",
                weight=25,
                levels={
                    "0": "Missing",
                    "5": "Named only",
                    "8": "Why WACC used",
                    "10": "WACC components discussed",
                },
            ),
            RubricCriterion(
                criterion="Terminal value",
                weight=25,
                levels={
                    "0": "Missing",
                    "5": "Mentioned",
                    "8": "One method explained",
                    "10": "Gordon growth + sensitivity awareness",
                },
            ),
            RubricCriterion(
                criterion="Equity bridge",
                weight=20,
                levels={
                    "0": "Missing",
                    "5": "Partial",
                    "8": "EV to equity correctly",
                    "10": "Includes net debt and shares context",
                },
            ),
        ],
    ),
    RubricDocument(
        role=Role.PRODUCT_MANAGER,
        question_id="prioritization_001",
        question="How do you prioritize features on a crowded roadmap?",
        ideal_answer=(
            "Align to strategy and outcomes, frame with RICE/ICE or value vs effort, "
            "use customer evidence, weigh dependencies and risk, communicate tradeoffs to stakeholders, "
            "revisit quarterly. STAR example of saying no to a high-profile request."
        ),
        evaluation_guidelines="Look for framework + stakeholder communication + real tradeoff example.",
        rubric=[
            RubricCriterion(
                criterion="Framework / method",
                weight=25,
                levels={
                    "0": "No method",
                    "5": "Generic gut feel",
                    "8": "Named framework",
                    "10": "Framework adapted to context",
                },
            ),
            RubricCriterion(
                criterion="Customer / data input",
                weight=25,
                levels={
                    "0": "None",
                    "5": "Mentions users",
                    "8": "Specific research or metrics",
                    "10": "Multiple evidence sources",
                },
            ),
            RubricCriterion(
                criterion="Stakeholder alignment",
                weight=25,
                levels={
                    "0": "None",
                    "5": "Mentions communication",
                    "8": "Tradeoff narrative",
                    "10": "Concrete example of saying no",
                },
            ),
            RubricCriterion(
                criterion="Outcome orientation",
                weight=25,
                levels={
                    "0": "Output focused only",
                    "5": "Some outcomes",
                    "8": "Metrics tied to priorities",
                    "10": "North star + guardrail metrics",
                },
            ),
        ],
    ),
]

SAMPLE_RUBRICS: list[RubricDocument] = _BASE_RUBRICS + BANK_RUBRICS
RUBRIC_BY_ID = build_rubric_index(SAMPLE_RUBRICS)

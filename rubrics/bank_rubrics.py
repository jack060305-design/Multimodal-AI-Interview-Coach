"""Rubrics for LangGraph question-bank prompts (Friday-style competency interviews).

Criteria follow STAR-style behavioral scoring (Situation, Task, Action, Result)
inspired by open guides such as ashishps1/awesome-behavioral-interviews.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from schemas import Role, RubricCriterion, RubricDocument


def _levels(
    zero: str, five: str, eight: str, ten: str
) -> dict[str, str]:
    return {"0": zero, "5": five, "8": eight, "10": ten}


def _criterion(name: str, weight: int, levels: dict[str, str]) -> RubricCriterion:
    return RubricCriterion(criterion=name, weight=weight, levels=levels)


# question_id -> (competency, difficulty) used by interview_agents/question_bank.py
BANK_QUESTION_META: dict[str, tuple[str, int]] = {
    "swe_intern_debug_001": ("problem_solving", 2),
    "swe_intern_git_001": ("collaboration", 2),
    "swe_intern_tradeoff_001": ("execution", 3),
    "da_metrics_001": ("problem_solving", 3),
    "da_ab_test_001": ("execution", 3),
    "da_stakeholder_001": ("communication", 2),
    "fa_variance_001": ("communication", 2),
    "fa_model_001": ("execution", 3),
    "fa_assumption_001": ("adaptability", 3),
    "pm_discovery_001": ("problem_solving", 3),
    "pm_roadmap_001": ("execution", 3),
    "pm_conflict_001": ("collaboration", 3),
}


BANK_RUBRICS: list[RubricDocument] = [
    RubricDocument(
        role=Role.SWE_INTERN,
        question_id="swe_intern_debug_001",
        question="How do you approach debugging a production issue?",
        ideal_answer=(
            "Reproduce or confirm scope (metrics, logs, alerts). Triage severity and "
            "communicate status. Form a hypothesis, gather evidence (logs, traces, recent "
            "deploys), bisect or roll back if needed. Fix with tests, deploy safely, verify "
            "recovery, and write a brief postmortem to prevent recurrence."
        ),
        evaluation_guidelines=(
            "Score on structured debugging, communication, and prevention. Full credit requires "
            "a concrete example with verification and follow-up."
        ),
        rubric=[
            _criterion(
                "Triage and communication",
                25,
                _levels(
                    "No process or ignores stakeholders",
                    "Mentions checking logs only",
                    "Assesses severity and updates team",
                    "Clear incident comms with timeline and owners",
                ),
            ),
            _criterion(
                "Hypothesis-driven investigation",
                30,
                _levels(
                    "Random guessing",
                    "Checks one source",
                    "Uses logs/metrics/deploy history",
                    "Systematic bisect with multiple signals",
                ),
            ),
            _criterion(
                "Resolution and safety",
                25,
                _levels(
                    "No fix or rollback plan",
                    "Hotfix without validation",
                    "Fix with basic verification",
                    "Fix, test, staged rollout, monitors green",
                ),
            ),
            _criterion(
                "Prevention / learning",
                20,
                _levels(
                    "Stops at fix",
                    "Mentions learning vaguely",
                    "Adds test or alert",
                    "Postmortem with actionable follow-ups",
                ),
            ),
        ],
    ),
    RubricDocument(
        role=Role.SWE_INTERN,
        question_id="swe_intern_git_001",
        question="Explain a merge conflict and how you resolved one.",
        ideal_answer=(
            "Merge conflicts occur when Git cannot auto-merge divergent edits to the same "
            "lines. I pull/rebase latest main, run merge or rebase, open conflicted files, "
            "read both sides and intent, resolve markers, run tests, commit, and push. "
            "I coordinate with the other author if logic overlap is unclear."
        ),
        evaluation_guidelines=(
            "Require accurate conflict cause, resolution steps, and collaboration. "
            "Penalize hand-waving without mentioning conflict markers or verification."
        ),
        rubric=[
            _criterion(
                "Understanding of merge conflicts",
                25,
                _levels(
                    "Cannot explain or blames Git incorrectly",
                    "Vague 'files clash'",
                    "Same lines/branches edited",
                    "Explains divergent history and markers",
                ),
            ),
            _criterion(
                "Resolution workflow",
                30,
                _levels(
                    "No concrete steps",
                    "Mentions git merge only",
                    "Pull, resolve markers, commit",
                    "Rebase/merge choice with test before push",
                ),
            ),
            _criterion(
                "Collaboration",
                25,
                _levels(
                    "Works in isolation only",
                    "Aware others exist",
                    "Coordinates on overlapping change",
                    "Pairs or documents resolution for reviewer",
                ),
            ),
            _criterion(
                "Concrete example (STAR)",
                20,
                _levels(
                    "No example",
                    "Hypothetical only",
                    "Real conflict with outcome",
                    "STAR example with lesson learned",
                ),
            ),
        ],
    ),
    RubricDocument(
        role=Role.SWE_INTERN,
        question_id="swe_intern_tradeoff_001",
        question="Describe a time you chose a simpler solution over a clever one.",
        ideal_answer=(
            "STAR story: deadline or maintainability drove choosing boring, well-tested "
            "approach over clever abstraction. Explain tradeoffs (speed, debt, readability), "
            "how you validated the choice, and what you would revisit later."
        ),
        evaluation_guidelines="Look for intentional tradeoff, not lack of skill. Reward clarity on when cleverness was deferred.",
        rubric=[
            _criterion(
                "Situation and constraints",
                25,
                _levels(
                    "No context",
                    "Vague project",
                    "Clear deadline or team constraint",
                    "Specific stakes and alternatives considered",
                ),
            ),
            _criterion(
                "Tradeoff reasoning",
                30,
                _levels(
                    "No tradeoff",
                    "Simpler because easier",
                    "Compares complexity vs risk",
                    "Explicit cost/benefit and maintainability",
                ),
            ),
            _criterion(
                "Execution and outcome",
                25,
                _levels(
                    "No result",
                    "Shipped unclear outcome",
                    "Delivered with measurable result",
                    "Delivered on time with quality metrics",
                ),
            ),
            _criterion(
                "Reflection",
                20,
                _levels(
                    "No reflection",
                    "Would do same always",
                    "Notes what to improve later",
                    "Plans when to refactor with criteria",
                ),
            ),
        ],
    ),
    RubricDocument(
        role=Role.DATA_ANALYST,
        question_id="da_metrics_001",
        question="How do you define and validate a product metric?",
        ideal_answer=(
            "Tie metric to user/business outcome (north star + guardrails). Define "
            "numerator/denominator, grain, filters, and ownership. Validate with sanity checks, "
            "historical trends, segment cuts, and an experiment or proxy ground truth. "
            "Document in a metric spec and monitor for drift."
        ),
        evaluation_guidelines="Require definition rigor and validation steps, not just naming a metric.",
        rubric=[
            _criterion(
                "Outcome alignment",
                25,
                _levels(
                    "Vanity metric only",
                    "Loosely related to product",
                    "Tied to user or revenue outcome",
                    "North star with guardrail metrics",
                ),
            ),
            _criterion(
                "Operational definition",
                30,
                _levels(
                    "No definition",
                    "Name only",
                    "Numerator/denominator stated",
                    "Grain, filters, exclusions documented",
                ),
            ),
            _criterion(
                "Validation approach",
                25,
                _levels(
                    "Ship and hope",
                    "One spot check",
                    "Trends and segment sanity checks",
                    "Experiment or source-of-truth reconciliation",
                ),
            ),
            _criterion(
                "Stakeholder communication",
                20,
                _levels(
                    "None",
                    "Shares number only",
                    "Explains definition to PM",
                    "Metric spec with caveats and dashboard",
                ),
            ),
        ],
    ),
    RubricDocument(
        role=Role.DATA_ANALYST,
        question_id="da_ab_test_001",
        question="Walk through how you would design an A/B test.",
        ideal_answer=(
            "Clarify hypothesis and primary metric. Define population, randomization unit, "
            "allocation, duration, and power/M DE. Plan guardrails, novelty effects, and "
            "interference. Pre-register analysis, run QA on assignment, analyze with proper "
            "stats, and recommend ship/iterate/no-ship."
        ),
        evaluation_guidelines="Penalize missing randomization unit or success criteria. Reward power and guardrails.",
        rubric=[
            _criterion(
                "Hypothesis and metrics",
                25,
                _levels(
                    "No hypothesis",
                    "Vague goal",
                    "Primary metric named",
                    "Primary + guardrails with expected direction",
                ),
            ),
            _criterion(
                "Design mechanics",
                30,
                _levels(
                    "Shows button to half users",
                    "Randomization mentioned",
                    "Unit, split, duration considered",
                    "Power calc, SRM checks, exclusion rules",
                ),
            ),
            _criterion(
                "Analysis plan",
                25,
                _levels(
                    "Peek and decide",
                    "p-value only at end",
                    "Fixed horizon analysis",
                    "Pre-registered test, segments, practical significance",
                ),
            ),
            _criterion(
                "Risks and ethics",
                20,
                _levels(
                    "Ignored",
                    "Mentions risk vaguely",
                    "Novelty or seasonality noted",
                    "Interference, fairness, and rollback plan",
                ),
            ),
        ],
    ),
    RubricDocument(
        role=Role.DATA_ANALYST,
        question_id="da_stakeholder_001",
        question="Tell me about presenting insights to a non-technical stakeholder.",
        ideal_answer=(
            "STAR: audience goal first, headline insight, visual simple chart, so-what and "
            "recommended action, anticipate objections, limit jargon, offer appendix for detail."
        ),
        evaluation_guidelines="Score storytelling and action orientation, not SQL depth.",
        rubric=[
            _criterion(
                "Audience framing",
                25,
                _levels(
                    "Dumps data",
                    "Some context",
                    "States decision to inform",
                    "Ties to stakeholder OKR",
                ),
            ),
            _criterion(
                "Clarity of insight",
                30,
                _levels(
                    "No takeaway",
                    "Buried lead",
                    "Clear headline finding",
                    "Headline + supporting evidence simply",
                ),
            ),
            _criterion(
                "Recommendation",
                25,
                _levels(
                    "No action",
                    "Generic next steps",
                    "Specific recommendation",
                    "Recommendation with tradeoffs and risks",
                ),
            ),
            _criterion(
                "Concrete example",
                20,
                _levels(
                    "Hypothetical only",
                    "Weak example",
                    "Real presentation",
                    "STAR with measurable business impact",
                ),
            ),
        ],
    ),
    RubricDocument(
        role=Role.FINANCE_ANALYST,
        question_id="fa_variance_001",
        question="How do you explain a budget variance to leadership?",
        ideal_answer=(
            "State variance magnitude and direction vs plan. Bridge drivers (volume, price, "
            "timing, one-offs). Separate controllable vs external. Use simple bridge chart, "
            "implications for forecast, and recommended actions."
        ),
        evaluation_guidelines="Require variance bridge thinking and executive-ready brevity.",
        rubric=[
            _criterion(
                "Variance framing",
                25,
                _levels(
                    "Number only",
                    "Favorable/unfavorable stated",
                    "Vs plan and prior period",
                    "Materiality and forecast impact",
                ),
            ),
            _criterion(
                "Driver analysis",
                30,
                _levels(
                    "No drivers",
                    "Single vague reason",
                    "Two to three drivers",
                    "Structured bridge with quantified drivers",
                ),
            ),
            _criterion(
                "Executive communication",
                25,
                _levels(
                    "Jargon heavy",
                    "Too much detail",
                    "Headline plus backup",
                    "Action-oriented summary with visuals",
                ),
            ),
            _criterion(
                "Forward look",
                20,
                _levels(
                    "Backward only",
                    "Mentions forecast",
                    "Updates outlook",
                    "Outlook with scenarios and asks",
                ),
            ),
        ],
    ),
    RubricDocument(
        role=Role.FINANCE_ANALYST,
        question_id="fa_model_001",
        question="What checks do you run before sharing a financial model?",
        ideal_answer=(
            "Integrity checks: balance sheet balances, signs/units, circular refs. "
            "Reasonableness vs history and benchmarks. Stress key assumptions. Version control, "
            "document assumptions, sensitivity tables, and peer review."
        ),
        evaluation_guidelines="Look for systematic QA, not just Excel tips.",
        rubric=[
            _criterion(
                "Structural integrity",
                30,
                _levels(
                    "No checks",
                    "Spot check one tab",
                    "Balance and sign checks",
                    "Full tie-outs and error tracing",
                ),
            ),
            _criterion(
                "Assumption reasonableness",
                25,
                _levels(
                    "Unchecked assumptions",
                    "Sanity glance",
                    "Vs history or comps",
                    "Sensitivity on top drivers",
                ),
            ),
            _criterion(
                "Documentation and reproducibility",
                25,
                _levels(
                    "Undocumented",
                    "Some labels",
                    "Assumption log",
                    "Versioned model with change log",
                ),
            ),
            _criterion(
                "Review process",
                20,
                _levels(
                    "Sends immediately",
                    "Self-review only",
                    "Peer review",
                    "Peer review plus stakeholder walkthrough",
                ),
            ),
        ],
    ),
    RubricDocument(
        role=Role.FINANCE_ANALYST,
        question_id="fa_assumption_001",
        question="Describe a time a key assumption in your analysis was wrong.",
        ideal_answer=(
            "STAR: assumption stated upfront, how error surfaced, impact quantified, "
            "corrective analysis, communication to stakeholders, and process change to catch "
            "similar issues."
        ),
        evaluation_guidelines="Reward accountability and process improvement, not blaming externals.",
        rubric=[
            _criterion(
                "Assumption clarity",
                25,
                _levels(
                    "Unclear story",
                    "Vague assumption",
                    "Named assumption and why used",
                    "Documented assumption with sensitivity",
                ),
            ),
            _criterion(
                "Detection and impact",
                30,
                _levels(
                    "Never noticed",
                    "Noticed late",
                    "Quantified impact",
                    "Early signal and revised forecast",
                ),
            ),
            _criterion(
                "Stakeholder handling",
                25,
                _levels(
                    "Hid error",
                    "Delayed disclosure",
                    "Transparent update",
                    "Proactive comms with options",
                ),
            ),
            _criterion(
                "Process improvement",
                20,
                _levels(
                    "No change",
                    "Personal caution only",
                    "Added one check",
                    "Team-wide control or template update",
                ),
            ),
        ],
    ),
    RubricDocument(
        role=Role.PRODUCT_MANAGER,
        question_id="pm_discovery_001",
        question="How do you run discovery when requirements are ambiguous?",
        ideal_answer=(
            "Frame problem and success metrics. Identify risky assumptions. Mix qual "
            "(interviews) and quant (funnel, support tickets). Synthesize themes, prototype "
            "or concierge test, align stakeholders on scope slice, iterate."
        ),
        evaluation_guidelines="Require assumption testing and evidence mix, not endless brainstorming.",
        rubric=[
            _criterion(
                "Problem framing",
                25,
                _levels(
                    "Jumps to solutions",
                    "Vague problem",
                    "User/job statement",
                    "Problem, constraints, and success metrics",
                ),
            ),
            _criterion(
                "Discovery methods",
                30,
                _levels(
                    "Guessing",
                    "Only surveys or only interviews",
                    "Qual + light quant",
                    "Targeted methods per riskiest assumption",
                ),
            ),
            _criterion(
                "Synthesis and prioritization",
                25,
                _levels(
                    "List of ideas",
                    "Themes without priority",
                    "Prioritized opportunities",
                    "Opportunity solution tree or ranked bets",
                ),
            ),
            _criterion(
                "Alignment output",
                20,
                _levels(
                    "No artifact",
                    "Notes only",
                    "PRD slice or prototype",
                    "Aligned spec with out-of-scope explicit",
                ),
            ),
        ],
    ),
    RubricDocument(
        role=Role.PRODUCT_MANAGER,
        question_id="pm_roadmap_001",
        question="Describe balancing tech debt against new features.",
        ideal_answer=(
            "Quantify debt cost (incidents, velocity). Align with strategy and capacity "
            "budget (e.g., 20% debt). Frame tradeoffs to eng and leadership, sequence debt "
            "that unlocks roadmap, communicate customer impact of both paths."
        ),
        evaluation_guidelines="Look for explicit capacity framing and stakeholder tradeoffs.",
        rubric=[
            _criterion(
                "Debt articulation",
                25,
                _levels(
                    "Labels everything debt",
                    "Generic maintenance",
                    "Names specific debt with impact",
                    "Quantified cost or risk of inaction",
                ),
            ),
            _criterion(
                "Prioritization framework",
                30,
                _levels(
                    "Always features or always debt",
                    "Ad hoc each sprint",
                    "Capacity allocation rule",
                    "Rule tied to outcomes and dependencies",
                ),
            ),
            _criterion(
                "Stakeholder management",
                25,
                _levels(
                    "Avoids conversation",
                    "Mentions eng only",
                    "Explains to leadership",
                    "Negotiated roadmap with visible tradeoffs",
                ),
            ),
            _criterion(
                "Example",
                20,
                _levels(
                    "No example",
                    "Hypothetical",
                    "Real sequencing decision",
                    "STAR with measurable velocity or reliability win",
                ),
            ),
        ],
    ),
    RubricDocument(
        role=Role.PRODUCT_MANAGER,
        question_id="pm_conflict_001",
        question="Tell me about aligning engineering and sales on priorities.",
        ideal_answer=(
            "STAR: surfaced misalignment on custom deal vs platform work. Listened to both, "
            "mapped to strategy and revenue impact, proposed phased plan or guardrails for "
            "custom work, facilitated joint roadmap review, documented decision."
        ),
        evaluation_guidelines="Score facilitation and outcome, not taking one side by default.",
        rubric=[
            _criterion(
                "Understanding both sides",
                25,
                _levels(
                    "Dismisses one function",
                    "Surface listening",
                    "Captures incentives of both",
                    "Articulates root conflict not positions",
                ),
            ),
            _criterion(
                "Strategy alignment",
                30,
                _levels(
                    "Picks louder voice",
                    "Compromise without criteria",
                    "Uses strategy or data",
                    "Ties decision to company goals and metrics",
                ),
            ),
            _criterion(
                "Facilitation and process",
                25,
                _levels(
                    "Escalates immediately",
                    "One-off meeting",
                    "Structured forum",
                    "Ongoing prioritization ritual with rules",
                ),
            ),
            _criterion(
                "Outcome",
                20,
                _levels(
                    "Unresolved",
                    "Temporary truce",
                    "Clear decision documented",
                    "Decision with follow-through and feedback loop",
                ),
            ),
        ],
    ),
]

"""Curated job-search / xin việc interview questions with STAR rubrics."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from schemas import Role
from rubrics.star_template import make_behavioral_rubric

# question_id -> (competency, difficulty)
JOB_SEARCH_META: dict[str, tuple[str, int]] = {
    "swe_job_intro_001": ("communication", 2),
    "swe_job_why_company_001": ("communication", 2),
    "swe_job_weakness_001": ("adaptability", 2),
    "swe_job_team_conflict_001": ("collaboration", 3),
    "da_job_intro_001": ("communication", 2),
    "da_job_why_analyst_001": ("communication", 2),
    "da_job_ambiguous_001": ("problem_solving", 3),
    "da_job_deadline_001": ("execution", 3),
    "fa_job_intro_001": ("communication", 2),
    "fa_job_why_finance_001": ("communication", 2),
    "fa_job_detail_pressure_001": ("execution", 3),
    "fa_job_assumption_challenge_001": ("adaptability", 3),
    "pm_job_intro_001": ("communication", 2),
    "pm_job_why_pm_001": ("communication", 2),
    "pm_job_say_no_001": ("execution", 3),
    "pm_job_user_empathy_001": ("problem_solving", 3),
}

JOB_SEARCH_RUBRICS = [
    make_behavioral_rubric(
        role=Role.SWE_INTERN,
        question_id="swe_job_intro_001",
        question="Tell me about yourself and why you are a strong fit for this software engineering role.",
    ),
    make_behavioral_rubric(
        role=Role.SWE_INTERN,
        question_id="swe_job_why_company_001",
        question="Why do you want to work at our company, and what excites you about this team?",
    ),
    make_behavioral_rubric(
        role=Role.SWE_INTERN,
        question_id="swe_job_weakness_001",
        question="What is your greatest weakness, and how are you actively improving it?",
    ),
    make_behavioral_rubric(
        role=Role.SWE_INTERN,
        question_id="swe_job_team_conflict_001",
        question="Tell me about a time you disagreed with a teammate on a technical decision. How did you resolve it?",
    ),
    make_behavioral_rubric(
        role=Role.DATA_ANALYST,
        question_id="da_job_intro_001",
        question="Walk me through your background and why you are pursuing a data analyst role.",
    ),
    make_behavioral_rubric(
        role=Role.DATA_ANALYST,
        question_id="da_job_why_analyst_001",
        question="Why do you want this analyst position, and how does it fit your career goals?",
    ),
    make_behavioral_rubric(
        role=Role.DATA_ANALYST,
        question_id="da_job_ambiguous_001",
        question="Describe a time you had to analyze data when the business question was ambiguous.",
    ),
    make_behavioral_rubric(
        role=Role.DATA_ANALYST,
        question_id="da_job_deadline_001",
        question="Tell me about a time you had to deliver analysis under a tight deadline.",
    ),
    make_behavioral_rubric(
        role=Role.FINANCE_ANALYST,
        question_id="fa_job_intro_001",
        question="Tell me about yourself and your experience relevant to finance analysis.",
    ),
    make_behavioral_rubric(
        role=Role.FINANCE_ANALYST,
        question_id="fa_job_why_finance_001",
        question="Why are you interested in this finance analyst role and our organization?",
    ),
    make_behavioral_rubric(
        role=Role.FINANCE_ANALYST,
        question_id="fa_job_detail_pressure_001",
        question="Describe a time attention to detail prevented a costly error in a model or report.",
    ),
    make_behavioral_rubric(
        role=Role.FINANCE_ANALYST,
        question_id="fa_job_assumption_challenge_001",
        question="Tell me about a time you challenged a key assumption in a financial forecast.",
    ),
    make_behavioral_rubric(
        role=Role.PRODUCT_MANAGER,
        question_id="pm_job_intro_001",
        question="Tell me about yourself and why you want to be a product manager.",
    ),
    make_behavioral_rubric(
        role=Role.PRODUCT_MANAGER,
        question_id="pm_job_why_pm_001",
        question="Why do you want to join our company as a PM, and what product problems interest you?",
    ),
    make_behavioral_rubric(
        role=Role.PRODUCT_MANAGER,
        question_id="pm_job_say_no_001",
        question="Describe a time you had to say no to a stakeholder request. How did you handle it?",
    ),
    make_behavioral_rubric(
        role=Role.PRODUCT_MANAGER,
        question_id="pm_job_user_empathy_001",
        question="Tell me about a time user research changed your product decision.",
    ),
]

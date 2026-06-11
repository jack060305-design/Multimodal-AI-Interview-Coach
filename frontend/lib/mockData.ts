export type Role = { id: string; label: string };
export type Question = { question_id: string; question: string };

export const MOCK_ROLES: Role[] = [
  { id: "swe_intern", label: "SWE Intern" },
  { id: "data_analyst", label: "Data Analyst" },
  { id: "finance_analyst", label: "Finance Analyst" },
  { id: "product_manager", label: "Product Manager" },
];

export const MOCK_QUESTIONS: Record<string, Question[]> = {
  swe_intern: [
    {
      question_id: "react_useeffect_001",
      question: "Explain how React useEffect works and when you would use it.",
    },
    {
      question_id: "js_basics_001",
      question: "What is the difference between let, const, and var in JavaScript?",
    },
    {
      question_id: "git_basics_001",
      question: "How do you resolve a merge conflict in Git?",
    },
  ],
  data_analyst: [
    {
      question_id: "sql_window_functions_001",
      question: "What are SQL window functions and give an example use case?",
    },
    {
      question_id: "sql_joins_001",
      question: "Explain the difference between INNER JOIN and LEFT JOIN.",
    },
  ],
  finance_analyst: [
    {
      question_id: "dcf_basics_001",
      question: "Walk me through a basic DCF valuation approach.",
    },
    {
      question_id: "finance_ratios_001",
      question: "What does the current ratio tell you about a company?",
    },
  ],
  product_manager: [
    {
      question_id: "prioritization_001",
      question: "How do you prioritize features on a crowded roadmap?",
    },
    {
      question_id: "pm_metrics_001",
      question: "What metrics would you track after launching a new feature?",
    },
  ],
};

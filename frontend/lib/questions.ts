export type BankQuestion = {
  question_id: string;
  question: string;
  competency?: string;
};

export function pickRandomQuestion(questions: BankQuestion[]): BankQuestion | null {
  if (!questions.length) return null;
  return questions[Math.floor(Math.random() * questions.length)];
}

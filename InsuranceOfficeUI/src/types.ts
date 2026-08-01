export interface Citation {
  policyName: string;
  pageNumber: number;
  url?: string | null;
  source: string;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

export interface Conversation {
  sessionId: string;
  status: "active";
  title: string;
  messageCount: number;
  createdAt: string;
  updatedAt: string;
}

export const SUGGESTIONS = [
  "→ How much to insure with a full coverage a €25,000 car for a 35 year-old who lives in Rome which has the lowest insurance merit class?",
  "→ Compare life insurance across the 3 companies",
  "→ Which company is cheapest for a €300,000 house based in Milan and owned by a 56 years old female?",
  "→ What does The Three Lines cover for car insurance?",
];

import type { AskResponse } from "./types";

export async function ask(question: string): Promise<AskResponse> {
  const response = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) {
    throw new Error(`The engine could not be reached (HTTP ${response.status}).`);
  }
  return (await response.json()) as AskResponse;
}

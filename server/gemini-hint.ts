import { GoogleGenAI } from "@google/genai";

// DON'T DELETE THIS COMMENT
// Follow these instructions when using this blueprint:
// - Note that the newest Gemini model series is "gemini-2.5-flash" or gemini-2.5-pro"
//   - do not change this unless explicitly requested by the user

// This API key is from Gemini Developer API Key, not vertex AI API Key
const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY || "" });

export interface SQLHint {
  issue_identified: string;
  concept_needed: string;
  hint: string;
  confidence: number;
}

export interface HintRequestContext {
  problemDescription: string;
  problemTitle: string;
  tables: Array<{
    name: string;
    columns: Array<{ name: string; type: string }>;
  }>;
  userQuery: string;
  feedback: string[];
  userOutput?: any[];
  expectedOutput?: any[];
}

export async function generateSQLHint(
  context: HintRequestContext
): Promise<SQLHint> {
  try {
    const systemPrompt = `You are an expert SQL tutor helping students learn by providing hints without giving away the solution.

Your role is to:
- Identify what's wrong with the student's SQL query
- Point out the SQL concept or technique they should use
- Give a helpful hint that guides them toward the solution WITHOUT writing the actual SQL code
- Be encouraging and educational

IMPORTANT RULES:
- NEVER write the complete SQL solution
- NEVER provide the exact query or query fragments
- Focus on concepts, approaches, and what to think about
- Keep hints concise and actionable (2-3 sentences max)
- Be supportive and educational`;

    const tableSchemas = context.tables
      .map(
        (table) =>
          `Table: ${table.name}\nColumns: ${table.columns.map((col) => `${col.name} (${col.type})`).join(", ")}`
      )
      .join("\n\n");

    const outputComparison =
      context.userOutput && context.expectedOutput
        ? `
STUDENT'S OUTPUT (sample):
${JSON.stringify(context.userOutput.slice(0, 3), null, 2)}

EXPECTED OUTPUT (sample):
${JSON.stringify(context.expectedOutput.slice(0, 3), null, 2)}`
        : "";

    const prompt = `Help this student debug their SQL query:

PROBLEM: ${context.problemTitle}
${context.problemDescription}

DATABASE SCHEMA:
${tableSchemas}

STUDENT'S QUERY:
${context.userQuery}

VALIDATION FEEDBACK:
${context.feedback.join("\n")}
${outputComparison}

Analyze what went wrong and provide a helpful hint. Respond with JSON in this exact format:
{
  "issue_identified": "Brief description of what's wrong",
  "concept_needed": "SQL concept/technique they should use",
  "hint": "Helpful hint without revealing the solution",
  "confidence": 0.9
}`;

    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      config: {
        systemInstruction: systemPrompt,
        responseMimeType: "application/json",
        responseSchema: {
          type: "object",
          properties: {
            issue_identified: { type: "string" },
            concept_needed: { type: "string" },
            hint: { type: "string" },
            confidence: { type: "number" },
          },
          required: [
            "issue_identified",
            "concept_needed",
            "hint",
            "confidence",
          ],
        },
      },
      contents: prompt,
    });

    const rawJson = response.text;

    if (rawJson) {
      const data: SQLHint = JSON.parse(rawJson);
      return data;
    } else {
      throw new Error("Empty response from Gemini");
    }
  } catch (error) {
    console.error("Error generating SQL hint:", error);
    throw new Error(`Failed to generate hint: ${error}`);
  }
}

"""
Gemini AI service for generating progressive SQL hints
Provides increasingly specific hints to help students learn step-by-step
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional
from enum import Enum
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY not found in environment variables")


class HintLevel(Enum):
    """Progressive hint levels from gentle to specific"""
    GENTLE = "gentle"  # High-level guidance
    MODERATE = "moderate"  # Point to specific concepts
    SPECIFIC = "specific"  # Detailed guidance without solution
    DETAILED = "detailed"  # Very specific, almost solution


class SQLHintGenerator:
    """Generate helpful, progressive SQL hints without revealing solutions"""

    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

    async def generate_hint(
            self,
            problem_title: str,
            problem_description: str,
            tables: List[Dict[str, Any]],
            user_query: str,
            feedback: List[str],
            hint_level: HintLevel = HintLevel.MODERATE,
            attempt_number: int = 1,
            user_output: Optional[List[Dict[str, Any]]] = None,
            expected_output: Optional[List[Dict[str, Any]]] = None,
            previous_hints: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate a helpful hint for a failed SQL submission with progressive difficulty

        Args:
            problem_title: Title of the SQL problem
            problem_description: Full problem description
            tables: Database schema information
            user_query: The student's SQL query that failed
            feedback: Validation feedback from the system
            hint_level: Level of hint specificity (gentle to detailed)
            attempt_number: Number of attempts made (adjusts hint specificity)
            user_output: Sample of user's query output (optional)
            expected_output: Sample of expected output (optional)
            previous_hints: List of previously given hints (optional)

        Returns:
            Dict containing:
            - category: Type of issue (e.g., "JOIN", "WHERE", "GROUP BY")
            - issue_identified: What's wrong
            - concept_needed: SQL concept to use
            - hint: Progressive hint based on level
            - example_concept: Simple example of the concept (not the solution)
            - next_steps: Actionable steps to try
            - confidence: AI confidence score
            - encouragement: Motivational message
        """
        try:
            # Auto-adjust hint level based on attempts
            if attempt_number > 3 and hint_level == HintLevel.GENTLE:
                hint_level = HintLevel.MODERATE
            elif attempt_number > 5 and hint_level == HintLevel.MODERATE:
                hint_level = HintLevel.SPECIFIC

            # Build table schemas with sample data hints
            table_schemas = self._build_table_schemas(tables)

            # Build output comparison
            output_comparison = self._build_output_comparison(
                user_output, expected_output)

            # Build previous hints context
            previous_hints_str = ""
            if previous_hints:
                previous_hints_str = "\nPREVIOUS HINTS GIVEN:\n" + "\n".join(
                    f"- {hint}" for hint in previous_hints[-3:]  # Last 3 hints
                )

            # Construct the system instruction
            system_instruction = self._build_system_instruction(
                hint_level, attempt_number)

            # Build the main prompt
            prompt = f"""Analyze this student's SQL query attempt and provide a {hint_level.value} hint:

PROBLEM: {problem_title}
{problem_description}

DATABASE SCHEMA:
{table_schemas}

STUDENT'S QUERY (Attempt #{attempt_number}):
```sql
{user_query}
```

VALIDATION FEEDBACK:
{chr(10).join(f"❌ {fb}" for fb in feedback)}
{output_comparison}
{previous_hints_str}

Provide a {hint_level.value} hint that helps them learn. Respond with JSON in this exact format:
{{
  "category": "Issue category (e.g., JOIN, WHERE, AGGREGATION, ORDER BY)",
  "issue_identified": "What's wrong in simple terms",
  "concept_needed": "SQL concept or technique needed",
  "hint": "{self._get_hint_instruction(hint_level)}",
  "example_concept": "Generic example of the concept (not using this problem's data)",
  "next_steps": ["step 1", "step 2", "step 3"],
  "sql_tip": "A general SQL best practice related to this issue",
  "confidence": 0.9,
  "encouragement": "Brief motivational message"
}}"""

            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json", temperature=0.7))

            hint_data = json.loads(response.text)

            # Validate and enhance response
            hint_data = self._validate_and_enhance_response(
                hint_data, hint_level, attempt_number)

            logger.info(
                f"Generated {hint_level.value} hint for attempt #{attempt_number}"
            )
            return hint_data

        except Exception as e:
            logger.error(f"Error generating SQL hint: {str(e)}", exc_info=True)
            return self._get_fallback_hint(feedback, attempt_number)

    def _build_table_schemas(self, tables: List[Dict[str, Any]]) -> str:
        """Build formatted table schemas with helpful annotations and sample data"""
        schemas = []
        for table in tables:
            columns = []
            for col in table.get('columns', []):
                col_str = f"  • {col['name']} ({col['type']})"
                if col.get('primary_key'):
                    col_str += " 🔑 PRIMARY KEY"
                if col.get('foreign_key'):
                    col_str += f" → {col['foreign_key']}"
                columns.append(col_str)

            schema = f"📋 Table: {table['name']}\n" + "\n".join(columns)
            
            # Add sample data if available - this helps AI understand actual values!
            sample_data = table.get('sampleData') or table.get('sample_data')
            if sample_data and len(sample_data) > 0:
                schema += f"\n\n  📊 Sample Data (first {min(5, len(sample_data))} rows):"
                for i, row in enumerate(sample_data[:5]):
                    schema += f"\n  Row {i+1}: {json.dumps(row, ensure_ascii=False)}"
                
                # Extract distinct values for categorical-looking columns
                if len(sample_data) > 1:
                    schema += "\n\n  💡 Distinct values found in sample:"
                    for col in table.get('columns', []):
                        col_name = col['name']
                        try:
                            distinct_vals = list(set(str(row.get(col_name, '')) for row in sample_data if col_name in row))
                            if len(distinct_vals) <= 10 and len(distinct_vals) > 0:  # Only show if reasonably small set
                                schema += f"\n    • {col_name}: {', '.join(repr(v) for v in sorted(distinct_vals) if v)}"
                        except:
                            pass  # Skip if there's any issue extracting values
            
            schemas.append(schema)

        return "\n\n".join(schemas)

    def _build_output_comparison(
            self, user_output: Optional[List[Dict[str, Any]]],
            expected_output: Optional[List[Dict[str, Any]]]) -> str:
        """Build formatted output comparison"""
        if not user_output or not expected_output:
            return ""

        return f"""
📊 OUTPUT COMPARISON:

Your Output (first 3 rows):
{json.dumps(user_output[:3], indent=2)}

Expected Output (first 3 rows):
{json.dumps(expected_output[:3], indent=2)}

💡 Look for differences in: column names, data types, values, row count, or ordering
"""

    def _build_system_instruction(self, hint_level: HintLevel,
                                  attempt_number: int) -> str:
        """Build context-aware system instruction"""
        base_instruction = """You are a supportive SQL tutor helping students learn through discovery.

Your goals:
✓ Help students understand SQL concepts deeply
✓ Provide hints that guide without giving away answers
✓ Be encouraging and build confidence
✓ Teach best practices and common patterns

CRITICAL RULES:
✗ NEVER write the complete solution query
✗ NEVER provide exact query fragments for this specific problem
✗ NEVER use the actual table/column names in example code
"""

        level_instructions = {
            HintLevel.GENTLE:
            "Give high-level conceptual guidance. Focus on WHAT to think about, not HOW to do it.",
            HintLevel.MODERATE:
            "Point to specific SQL concepts and clauses. Explain WHERE in the query to focus.",
            HintLevel.SPECIFIC:
            "Provide detailed guidance about the approach. You may mention clause structures but not the exact solution.",
            HintLevel.DETAILED:
            "Give very detailed guidance that brings them close to the solution, but still requires them to implement it."
        }

        encouragement = ""
        if attempt_number > 3:
            encouragement = f"\n\nThe student has tried {attempt_number} times - be extra supportive and clear."

        return base_instruction + level_instructions[hint_level] + encouragement

    def _get_hint_instruction(self, hint_level: HintLevel) -> str:
        """Get instruction for hint field based on level"""
        instructions = {
            HintLevel.GENTLE:
            "General guidance about the approach (2-3 sentences)",
            HintLevel.MODERATE:
            "Point to specific SQL concepts to use (2-3 sentences)",
            HintLevel.SPECIFIC:
            "Detailed guidance about the structure needed (3-4 sentences)",
            HintLevel.DETAILED:
            "Very specific guidance that almost reveals the solution (4-5 sentences)"
        }
        return instructions[hint_level]

    def _validate_and_enhance_response(self, hint_data: Dict[str, Any],
                                       hint_level: HintLevel,
                                       attempt_number: int) -> Dict[str, Any]:
        """Validate response structure and add metadata"""
        required_fields = [
            "category", "issue_identified", "concept_needed", "hint",
            "confidence", "encouragement"
        ]

        # Ensure all required fields exist
        for field in required_fields:
            if field not in hint_data:
                hint_data[field] = "Information not available"

        # Add metadata
        hint_data["hint_level"] = hint_level.value
        hint_data["attempt_number"] = attempt_number
        hint_data["timestamp"] = self._get_timestamp()

        # Ensure next_steps is a list
        if "next_steps" not in hint_data or not isinstance(
                hint_data["next_steps"], list):
            hint_data["next_steps"] = [
                "Review the problem requirements",
                "Check your query structure",
                "Test with a simpler version first"
            ]

        return hint_data

    def _get_fallback_hint(self, feedback: List[str],
                           attempt_number: int) -> Dict[str, Any]:
        """Return user-friendly fallback hint when AI fails"""
        encouragement = "You're making progress! " if attempt_number > 1 else "Great start! "

        return {
            "category":
            "GENERAL",
            "issue_identified":
            "There's a mismatch between your output and expected results",
            "concept_needed":
            "Query validation and result comparison",
            "hint":
            f"{encouragement}Compare your query output with the expected results. Focus on column names, data types, and the number of rows returned.",
            "example_concept":
            "When debugging SQL, start by running parts of your query separately to isolate the issue.",
            "next_steps": [
                "Check if all required columns are in your SELECT",
                "Verify your JOIN conditions",
                "Review your WHERE clause filters",
                "Check your GROUP BY and ORDER BY clauses"
            ],
            "sql_tip":
            "Use LIMIT to test your query with a small result set first.",
            "confidence":
            0.3,
            "encouragement":
            "Don't worry! Debugging SQL is a normal part of learning. Keep trying!",
            "hint_level":
            "moderate",
            "attempt_number":
            attempt_number,
            "timestamp":
            self._get_timestamp()
        }

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"


# Factory function for easy access
def create_hint_generator() -> SQLHintGenerator:
    """Create and return a hint generator instance"""
    return SQLHintGenerator()


# Global instance with convenience method
sql_hint_generator = SQLHintGenerator()


async def get_progressive_hint(problem_title: str,
                               problem_description: str,
                               tables: List[Dict[str, Any]],
                               user_query: str,
                               feedback: List[str],
                               attempt_number: int = 1,
                               **kwargs) -> Dict[str, Any]:
    """
    Convenience function for getting progressive hints
    Automatically adjusts hint level based on attempt number
    """
    # Auto-select hint level
    if attempt_number == 1:
        hint_level = HintLevel.GENTLE
    elif attempt_number <= 3:
        hint_level = HintLevel.MODERATE
    elif attempt_number <= 5:
        hint_level = HintLevel.SPECIFIC
    else:
        hint_level = HintLevel.DETAILED

    return await sql_hint_generator.generate_hint(
        problem_title=problem_title,
        problem_description=problem_description,
        tables=tables,
        user_query=user_query,
        feedback=feedback,
        hint_level=hint_level,
        attempt_number=attempt_number,
        **kwargs)

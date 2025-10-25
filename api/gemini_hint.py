"""
Gemini AI service for generating progressive SQL hints
Provides increasingly specific hints to help students learn step-by-step
"""
import os
import json
import logging
import hashlib
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
        # Use gemini-2.0-flash-exp with lower temperature for consistency
        self.model = genai.GenerativeModel(
            'gemini-2.5-flash-lite',
            generation_config=genai.GenerationConfig(
                temperature=
                0.5,  # Lower temp = more consistent, less creative (saves tokens on retries)
                response_mime_type="application/json"))
        # Simple in-memory cache to avoid duplicate API calls (reduces token usage)
        self._hint_cache = {}  # Cache format: {cache_key: hint_result}
        self.MAX_CACHE_SIZE = 100  # Prevent memory bloat

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
            # Simplified 2-level hint system to reduce token usage
            # Attempt 1: MODERATE (helpful guidance)
            # Attempt 2+: DETAILED (very specific, almost solution)
            if attempt_number == 1:
                hint_level = HintLevel.MODERATE
            else:
                hint_level = HintLevel.DETAILED

            # Check cache to avoid duplicate API calls
            cache_key = self._generate_cache_key(problem_title, user_query,
                                                 feedback, hint_level)
            if cache_key in self._hint_cache:
                logger.info(f"Cache hit for hint (saved tokens)")
                cached_hint = self._hint_cache[cache_key].copy()
                cached_hint["cached"] = True
                return cached_hint

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

            # Build compact prompt to reduce token usage
            hint_instruction = "Point to SQL concepts needed" if hint_level == HintLevel.MODERATE else "Detailed guidance with structure"

            prompt = f"""SQL Query Analysis - Attempt {attempt_number}

PROBLEM: {problem_title}
{problem_description}

SCHEMA & DATA:
{table_schemas}

QUERY:
```sql
{user_query}
```

ERRORS: {', '.join(feedback)}
{output_comparison}

Provide {hint_level.value} hint. JSON format:
{{
  "category": "Issue type",
  "issue_identified": "What's wrong",
  "concept_needed": "SQL concept needed",
  "hint": "{hint_instruction}",
  "example_concept": "Generic example",
  "next_steps": ["step1", "step2"],
  "sql_tip": "Best practice tip",
  "confidence": 0.9,
  "encouragement": "Brief message"
}}"""

            # Generate response (using model's default config set in __init__)
            response = self.model.generate_content(prompt)

            hint_data = json.loads(response.text)

            # Validate and enhance response
            hint_data = self._validate_and_enhance_response(
                hint_data, hint_level, attempt_number)

            # Cache the result to save tokens on repeated queries
            self._cache_hint(cache_key, hint_data)

            logger.info(
                f"Generated {hint_level.value} hint for attempt #{attempt_number}"
            )
            return hint_data

        except Exception as e:
            logger.error(f"Error generating SQL hint: {str(e)}", exc_info=True)
            return self._get_fallback_hint(feedback, attempt_number)

    def _build_table_schemas(self, tables: List[Dict[str, Any]]) -> str:
        """Build formatted table schemas with helpful annotations and sample data (optimized for token usage)"""
        schemas = []
        for table in tables:
            columns = []
            for col in table.get('columns', []):
                col_str = f"  • {col['name']} ({col['type']})"
                if col.get('primary_key'):
                    col_str += " 🔑 PK"
                if col.get('foreign_key'):
                    col_str += f" → {col['foreign_key']}"
                columns.append(col_str)

            schema = f"📋 {table['name']}\n" + "\n".join(columns)

            # Add minimal sample data - only 3 rows to reduce tokens
            sample_data = table.get('sampleData') or table.get('sample_data')
            if sample_data and len(sample_data) > 0:
                schema += f"\n  Sample ({min(3, len(sample_data))} rows):"
                for row in sample_data[:3]:
                    schema += f"\n  {json.dumps(row, ensure_ascii=False)}"

                # Only show distinct values for key columns (reduce token usage)
                if len(sample_data) > 1:
                    schema += "\n  Key values:"
                    for col in table.get('columns', []):
                        col_name = col['name']
                        try:
                            distinct_vals = list(
                                set(
                                    str(row.get(col_name, ''))
                                    for row in sample_data if col_name in row))
                            # Only show columns with 2-8 distinct values (likely categorical/filter columns)
                            if 2 <= len(distinct_vals) <= 8:
                                schema += f"\n    {col_name}: {', '.join(repr(v) for v in sorted(distinct_vals) if v)}"
                        except:
                            pass

            schemas.append(schema)

        return "\n\n".join(schemas)

    def _build_output_comparison(
            self, user_output: Optional[List[Dict[str, Any]]],
            expected_output: Optional[List[Dict[str, Any]]]) -> str:
        """Build formatted output comparison (optimized for token usage)"""
        if not user_output or not expected_output:
            return ""

        # Compact output comparison to reduce tokens
        return f"""
📊 OUTPUT:
Your result (first 2): {json.dumps(user_output[:2], ensure_ascii=False)}
Expected (first 2): {json.dumps(expected_output[:2], ensure_ascii=False)}
Rows: {len(user_output)} vs {len(expected_output)} expected
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

    def _generate_cache_key(self, problem_title: str, user_query: str,
                            feedback: List[str], hint_level: HintLevel) -> str:
        """Generate cache key from query parameters to avoid duplicate API calls"""
        # Normalize query by removing extra whitespace
        normalized_query = " ".join(user_query.strip().split())
        feedback_str = "|".join(sorted(feedback))

        cache_input = f"{problem_title}|{normalized_query}|{feedback_str}|{hint_level.value}"
        return hashlib.md5(cache_input.encode()).hexdigest()

    def _cache_hint(self, cache_key: str, hint_data: Dict[str, Any]) -> None:
        """Cache hint result with size limit"""
        # Implement simple LRU by clearing cache when full
        if len(self._hint_cache) >= self.MAX_CACHE_SIZE:
            # Clear half the cache (simple approach)
            keys_to_remove = list(
                self._hint_cache.keys())[:self.MAX_CACHE_SIZE // 2]
            for key in keys_to_remove:
                del self._hint_cache[key]

        self._hint_cache[cache_key] = hint_data

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
    Simplified 2-level system: Attempt 1 = moderate, Attempt 2+ = detailed
    """
    # Simplified hint level selection (reduces token usage)
    hint_level = HintLevel.MODERATE if attempt_number == 1 else HintLevel.DETAILED

    return await sql_hint_generator.generate_hint(
        problem_title=problem_title,
        problem_description=problem_description,
        tables=tables,
        user_query=user_query,
        feedback=feedback,
        hint_level=hint_level,
        attempt_number=attempt_number,
        **kwargs)

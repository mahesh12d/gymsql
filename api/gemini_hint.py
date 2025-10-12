"""
Gemini AI service for generating SQL hints without revealing solutions
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY not found in environment variables")


class SQLHintGenerator:
    """Generate helpful SQL hints without revealing solutions"""
    
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    async def generate_hint(
        self,
        problem_title: str,
        problem_description: str,
        tables: List[Dict[str, Any]],
        user_query: str,
        feedback: List[str],
        user_output: Optional[List[Dict[str, Any]]] = None,
        expected_output: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate a helpful hint for a failed SQL submission
        
        Args:
            problem_title: Title of the SQL problem
            problem_description: Full problem description
            tables: Database schema information
            user_query: The student's SQL query that failed
            feedback: Validation feedback from the system
            user_output: Sample of user's query output (optional)
            expected_output: Sample of expected output (optional)
        
        Returns:
            Dict containing issue_identified, concept_needed, hint, and confidence
        """
        try:
            # Build table schemas string
            table_schemas = []
            for table in tables:
                columns = ", ".join([
                    f"{col['name']} ({col['type']})" 
                    for col in table.get('columns', [])
                ])
                table_schemas.append(f"Table: {table['name']}\nColumns: {columns}")
            
            table_schemas_str = "\n\n".join(table_schemas)
            
            # Build output comparison if available
            output_comparison = ""
            if user_output and expected_output:
                output_comparison = f"""
STUDENT'S OUTPUT (sample):
{json.dumps(user_output[:3], indent=2)}

EXPECTED OUTPUT (sample):
{json.dumps(expected_output[:3], indent=2)}
"""
            
            # Construct the prompt
            system_instruction = """You are an expert SQL tutor helping students learn by providing hints without giving away the solution.

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
- Be supportive and educational"""

            prompt = f"""Help this student debug their SQL query:

PROBLEM: {problem_title}
{problem_description}

DATABASE SCHEMA:
{table_schemas_str}

STUDENT'S QUERY:
{user_query}

VALIDATION FEEDBACK:
{chr(10).join(feedback)}
{output_comparison}

Analyze what went wrong and provide a helpful hint. Respond with JSON in this exact format:
{{
  "issue_identified": "Brief description of what's wrong",
  "concept_needed": "SQL concept/technique they should use",
  "hint": "Helpful hint without revealing the solution",
  "confidence": 0.9
}}"""

            # Generate response with JSON mode
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.7
                )
            )
            
            # Parse the JSON response
            hint_data = json.loads(response.text)
            
            # Validate response structure
            required_fields = ["issue_identified", "concept_needed", "hint", "confidence"]
            if not all(field in hint_data for field in required_fields):
                raise ValueError("Invalid response structure from Gemini")
            
            logger.info(f"Generated SQL hint successfully")
            return hint_data
            
        except Exception as e:
            logger.error(f"Error generating SQL hint: {str(e)}", exc_info=True)
            # Return a fallback hint
            return {
                "issue_identified": "Unable to analyze the specific issue",
                "concept_needed": "Review the problem requirements",
                "hint": "Try comparing your output with the expected results carefully. Look for differences in column names, data types, or row ordering.",
                "confidence": 0.3
            }


# Global instance
sql_hint_generator = SQLHintGenerator()

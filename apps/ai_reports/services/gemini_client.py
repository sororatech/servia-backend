import os
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

CV_SCREENING_PROMPT = """
You are a hospitality recruitment expert. Evaluate this candidate's 
CV against the job requirements.

JOB REQUIREMENTS:
{job_description}

CANDIDATE CV TEXT:
{cv_text}

Return a JSON object with:
{{
    "fit_score": int (0-100),
    "summary": str (2-3 sentences),
    "strengths": [str],
    "weaknesses": [str],
    "feedback": str (personalized message to candidate)
}}

Focus on: customer service experience, communication skills, 
teamwork, professionalism, hotel experience.

Return ONLY the JSON object — no extra text, no markdown, 
no code blocks.
Keep the summary concise and return at most 4 strengths and 3 weaknesses.
"""


class GeminiConfigurationError(Exception):
    """Raised when Gemini client settings are missing or invalid."""


class GeminiResponseError(Exception):
    """Raised when Gemini returns an invalid payload."""


CV_SCREENING_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["fit_score", "summary", "strengths", "weaknesses", "feedback"],
    "properties": {
        "fit_score": {"type": "integer"},
        "summary": {"type": "string"},
        "strengths": {
            "type": "array",
            "items": {"type": "string"},
        },
        "weaknesses": {
            "type": "array",
            "items": {"type": "string"},
        },
        "feedback": {"type": "string"},
    },
}


def extract_json_object(response_text: str) -> dict:
    """Extract the first JSON object from a Gemini text response."""
    cleaned_text = response_text.strip()

    if cleaned_text.startswith('```'):
        parts = cleaned_text.split('```')
        if len(parts) >= 2:
            cleaned_text = parts[1]
        if cleaned_text.startswith('json'):
            cleaned_text = cleaned_text[4:]
        cleaned_text = cleaned_text.strip()

    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        start_index = cleaned_text.find('{')
        end_index = cleaned_text.rfind('}')
        if start_index == -1 or end_index == -1 or end_index <= start_index:
            raise
        return json.loads(cleaned_text[start_index:end_index + 1])


def get_gemini_client():
    """Get configured Gemini Flash model."""
    if not os.getenv('GEMINI_API_KEY'):
        raise GeminiConfigurationError("GEMINI_API_KEY is not configured.")
    return genai.GenerativeModel('gemini-2.5-flash')


def analyze_cv(cv_text: str, job_description: str, max_retries: int = 3) -> dict:
    """
    Send CV text to Gemini Flash for analysis.
    Returns parsed JSON response.
    """
    model = get_gemini_client()
    prompt = CV_SCREENING_PROMPT.format(
        job_description=job_description,
        cv_text=cv_text
    )

    last_error = None

    for attempt in range(max_retries):
        try:
            print(f"Gemini API attempt {attempt + 1}/{max_retries}")

            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0,
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                    response_schema=CV_SCREENING_RESPONSE_SCHEMA,
                ),
                request_options={'timeout': 30}
            )

           
            response_text = response.text.strip()

           
            result = extract_json_object(response_text)

           
            required_fields = ['fit_score', 'summary', 'strengths', 'weaknesses', 'feedback']
            for field in required_fields:
                if field not in result:
                    raise GeminiResponseError(f"Missing required field: {field}")

           
            if not isinstance(result['fit_score'], int) or not 0 <= result['fit_score'] <= 100:
                raise GeminiResponseError(
                    f"fit_score must be integer 0-100, got: {result['fit_score']}"
                )

         
            if not isinstance(result['strengths'], list):
                raise GeminiResponseError("strengths must be a list")
            if not isinstance(result['weaknesses'], list):
                raise GeminiResponseError("weaknesses must be a list")

            print(f"Gemini response received — fit_score: {result['fit_score']}")
            return result

        except json.JSONDecodeError as e:
            last_error = f"JSON parse error: {e}"
            print(f"Attempt {attempt + 1} failed: {last_error}")

        except GeminiResponseError as e:
            last_error = f"Validation error: {e}"
            print(f"Attempt {attempt + 1} failed: {last_error}")

        except GeminiConfigurationError:
            raise

        except Exception as e:
            last_error = f"API error: {e}"
            print(f"Attempt {attempt + 1} failed: {last_error}")

      
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)

    raise GeminiResponseError(
        f"Gemini API failed after {max_retries} attempts. Last error: {last_error}"
    )

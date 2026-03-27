import os
import re
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

CV_SCREENING_PROMPT = """
You are an expert recruiter. Evaluate this candidate's CV strictly
against the provided job requirements.

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
    "feedback": str (personalized message to candidate),
    "extracted_skills": [str] (list of specific skills, tools, technologies, and competencies found in the CV)
}}

Derive your evaluation criteria entirely from the JOB REQUIREMENTS above.
Weight job-specific skills and experience heavily. Generic soft skills
(communication, teamwork) should only contribute if they are explicitly
required by the job. A candidate with an unrelated background should
score very low even if they have transferable soft skills.

For extracted_skills, list every concrete skill mentioned in the CV
(e.g. "Python", "Project Management", "Adobe Photoshop", "Guest Relations").
Return up to 20 skills.

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
    "required": ["fit_score", "summary", "strengths", "weaknesses", "feedback", "extracted_skills"],
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
        "extracted_skills": {
            "type": "array",
            "items": {"type": "string"},
        },
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


PRIMARY_MODEL = 'gemini-2.5-flash'
FALLBACK_MODEL = 'gemini-2.5-pro'


def _strip_pii(text: str) -> str:
    """Remove PII before sending to AI."""
    # Remove email addresses
    text = re.sub(r'[\w.-]+@[\w.-]+', '[EMAIL]', text)
    # Remove phone numbers (E.164 + common formats)
    text = re.sub(r'\+?\d{1,3}[-.\s]?(?:\d{1,4})?[-.\s]?\d{1,4}[-.\s]?\d{1,9}', '[PHONE]', text)
    # Remove full names (basic heuristic: Capitalized words after "Name:" or at start)
    text = re.sub(r'(?i)(name:\s*)[A-Z][a-z]+\s+[A-Z][a-z]+', r'\1[NAME]', text)
    return text


def get_gemini_client(model: str = PRIMARY_MODEL):
    """Get configured Gemini model."""
    if not os.getenv('GEMINI_API_KEY'):
        raise GeminiConfigurationError("GEMINI_API_KEY is not configured.")
    return genai.GenerativeModel(model)


def _call_model(model, prompt: str) -> dict:
    """Send prompt to a Gemini model and return validated result dict."""
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

    result = extract_json_object(response.text.strip())

    required_fields = ['fit_score', 'summary', 'strengths', 'weaknesses', 'feedback', 'extracted_skills']
    for field in required_fields:
        if field not in result:
            raise GeminiResponseError(f"Missing required field: {field}")

    if not isinstance(result['fit_score'], int) or not 0 <= result['fit_score'] <= 100:
        raise GeminiResponseError(f"fit_score must be integer 0-100, got: {result['fit_score']}")

    if not isinstance(result['strengths'], list):
        raise GeminiResponseError("strengths must be a list")
    if not isinstance(result['weaknesses'], list):
        raise GeminiResponseError("weaknesses must be a list")
    if not isinstance(result['extracted_skills'], list):
        raise GeminiResponseError("extracted_skills must be a list")

    return result


def analyze_cv(cv_text: str, job_description: str, max_retries: int = 3) -> dict:
    """
    Send CV text to Gemini for analysis.
    Tries the primary model (Flash) with retries, then falls back to the Pro model on API failures.
    Returns parsed JSON response.
    """
    cv_text = _strip_pii(cv_text)
    prompt = CV_SCREENING_PROMPT.format(
        job_description=job_description,
        cv_text=cv_text
    )

    last_error = None
    api_failure = False  # tracks whether failure was an API error (not a validation error)

    primary_model = get_gemini_client(PRIMARY_MODEL)

    for attempt in range(max_retries):
        try:
            print(f"Gemini API attempt {attempt + 1}/{max_retries} (model: {PRIMARY_MODEL})")
            result = _call_model(primary_model, prompt)
            print(f"Gemini response received — fit_score: {result['fit_score']}")
            return result

        except (json.JSONDecodeError, GeminiResponseError) as e:
            last_error = str(e)
            api_failure = False
            print(f"Attempt {attempt + 1} failed (validation): {last_error}")

        except GeminiConfigurationError:
            raise

        except Exception as e:
            last_error = str(e)
            api_failure = True
            print(f"Attempt {attempt + 1} failed (API error): {last_error}")

        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)

    if api_failure:
        print(f"Primary model exhausted — falling back to {FALLBACK_MODEL}")
        try:
            fallback_model = get_gemini_client(FALLBACK_MODEL)
            result = _call_model(fallback_model, prompt)
            print(f"Fallback model succeeded — fit_score: {result['fit_score']}")
            return result
        except Exception as e:
            last_error = str(e)
            print(f"Fallback model also failed: {last_error}")

    raise GeminiResponseError(
        f"Gemini API failed after {max_retries} attempts. Last error: {last_error}"
    )

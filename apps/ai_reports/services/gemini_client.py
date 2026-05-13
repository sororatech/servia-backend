import os
import re
import json
import time
import logging
import google.generativeai as genai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

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
    "extracted_skills": [str] (list of specific skills, tools, technologies, and competencies found in the CV),
    "skills_match_details": {{
        "matched_skills": [str],
        "missing_skills": [str],
        "match_explanation": str (1-2 sentences explaining the match)
    }}
}}

Derive your evaluation criteria entirely from the JOB REQUIREMENTS above.
Weight job-specific skills and experience heavily. Generic soft skills
(communication, teamwork) should only contribute if they are explicitly
required by the job. A candidate with an unrelated background should
score very low even if they have transferable soft skills.

For extracted_skills, list every concrete skill mentioned in the CV
(e.g. "Python", "Project Management", "Adobe Photoshop", "Guest Relations").
Return up to 20 skills.

For skills_match_details:
- matched_skills: List skills from the CV that satisfy job requirements (include synonyms, e.g., "web development" matches "HTML/CSS")
- missing_skills: List key job requirements NOT found in the CV
- match_explanation: Briefly explain how the candidate's skills align with the job (e.g., "Candidate's web development experience covers the required HTML/CSS skills")

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
    "required": ["fit_score", "summary", "strengths", "weaknesses", "feedback", "extracted_skills", "skills_match_details"],
    "properties": {
        "fit_score": {"type": "integer"},
        "summary": {"type": "string"},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "weaknesses": {"type": "array", "items": {"type": "string"}},
        "feedback": {"type": "string"},
        "extracted_skills": {"type": "array", "items": {"type": "string"}},
        "skills_match_details": {
            "type": "object",
            "required": ["matched_skills", "missing_skills", "match_explanation"],
            "properties": {
                "matched_skills": {"type": "array", "items": {"type": "string"}},
                "missing_skills": {"type": "array", "items": {"type": "string"}},
                "match_explanation": {"type": "string"},
            },
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
    text = re.sub(r'[\w.-]+@[\w.-]+', '[EMAIL]', text)
    text = re.sub(r'\+?\d{1,3}[-.\s]?(?:\d{1,4})?[-.\s]?\d{1,4}[-.\s]?\d{1,9}', '[PHONE]', text)
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

    required_fields = ['fit_score', 'summary', 'strengths', 'weaknesses', 'feedback', 'extracted_skills', 'skills_match_details']
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


FOLLOW_UP_PROMPT = """You are an expert interview assistant for the hospitality recruitment industry.

{context_block}The candidate just said:
"{candidate_text}"

Generate exactly 3 sharp follow-up interview questions based on this specific response.
Questions should probe deeper — ask for concrete examples, clarify vague claims, or test the depth of stated skills.

Return ONLY a valid JSON array of 3 strings. No explanation, no markdown.
Example: ["Question 1?", "Question 2?", "Question 3?"]"""

INTERVIEW_ANALYSIS_PROMPT = """You are an expert recruitment analyst for the hospitality industry.

Below are all of the candidate's responses during the interview (numbered chronologically):

{candidate_transcript}

Analyse the candidate's overall performance and return a JSON object with exactly these fields:
{{
    "fit_score": <integer 0-100>,
    "summary": "<2-3 sentence overall assessment>",
    "strengths": ["strength1", "strength2", "strength3"],
    "weaknesses": ["weakness1", "weakness2"],
    "feedback": "<personalised 2-3 sentence feedback message addressed directly to the candidate>",
    "extracted_skills": ["skill1", "skill2", ...],
    "recommendation": "<hire|hold|reject>",
    "confidence": "<high|medium|low>"
}}

Return ONLY valid JSON — no markdown, no code blocks, no explanation."""

INTERVIEW_ANALYSIS_SCHEMA = {
    "type": "object",
    "required": ["fit_score", "summary", "strengths", "weaknesses", "feedback",
                 "extracted_skills", "recommendation", "confidence"],
    "properties": {
        "fit_score":        {"type": "integer"},
        "summary":          {"type": "string"},
        "strengths":        {"type": "array", "items": {"type": "string"}},
        "weaknesses":       {"type": "array", "items": {"type": "string"}},
        "feedback":         {"type": "string"},
        "extracted_skills": {"type": "array", "items": {"type": "string"}},
        "recommendation":   {"type": "string"},
        "confidence":       {"type": "string"},
    },
}

FOLLOW_UP_RESPONSE_SCHEMA = {
    "type": "array",
    "items": {"type": "string"},
}


def _extract_questions_from_text(text: str) -> list:
    """Best-effort extraction for non-JSON Gemini follow-up responses."""
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        if len(parts) >= 2:
            cleaned = parts[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
        if isinstance(parsed, dict):
            questions = parsed.get("questions")
            if isinstance(questions, list):
                return [str(item).strip() for item in questions if str(item).strip()]
    except Exception:
        pass

    question_candidates = re.findall(r'[^?]*\?', cleaned)
    normalized = []
    for question in question_candidates:
        question = question.strip(" \n\r\t-`\"'")
        if question:
            normalized.append(question)
    return normalized


def _fallback_follow_up_questions(candidate_text: str, context: list | None = None) -> list:
    """Generate reasonable probing questions when Gemini is unavailable."""
    text = re.sub(r"\s+", " ", (candidate_text or "").strip())
    if not text:
        return []

    keyword_patterns = [
        (r"\b(team|managed|supervised|led|trained)\b", "Can you share a specific example of how you led or supported your team and what result came from it?"),
        (r"\b(guest|customer|complaint|escalation|service)\b", "Tell me about a difficult guest situation you handled personally. What did you do, and what was the outcome?"),
        (r"\b(opera|pms|system|software|tool|excel|pos)\b", "How have you used those systems or tools in day-to-day work, and which tasks were you personally responsible for?"),
        (r"\b(sales|revenue|booking|occupancy|upsell)\b", "Can you give a concrete example of how your work improved bookings, revenue, or guest experience?"),
        (r"\b(training|mentor|onboard)\b", "What approach did you use when training new team members, and how did you know the training was effective?"),
        (r"\b(conflict|pressure|busy|peak|deadline)\b", "Describe a high-pressure moment in that role. How did you prioritize, and what was the result?"),
    ]

    questions = []
    for pattern, question in keyword_patterns:
        if re.search(pattern, text, re.IGNORECASE) and question not in questions:
            questions.append(question)
        if len(questions) == 3:
            return questions

    generic_questions = [
        "Can you walk me through one specific example that shows this experience in practice?",
        "What was your exact responsibility in that situation, and how did you measure success?",
        "What did you learn from that experience, and how would you apply it in this role?",
    ]
    for question in generic_questions:
        if question not in questions:
            questions.append(question)
        if len(questions) == 3:
            break

    return questions[:3]


def generate_follow_up_questions(candidate_text: str, context: list) -> list:
    """
    Called after each candidate response during a live interview.
    Returns a list of 3 follow-up questions, or [] on failure.
    Uses Flash model for low latency.
    """
    context_block = ""
    if len(context) > 1:
        prior = "\n".join(f"- {t}" for t in context[:-1])
        context_block = f"Previous candidate responses for context:\n{prior}\n\n"

    prompt = FOLLOW_UP_PROMPT.format(
        context_block=context_block,
        candidate_text=candidate_text,
    )

    try:
        model = get_gemini_client(PRIMARY_MODEL)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0,
                max_output_tokens=256,
                response_mime_type="application/json",
                response_schema=FOLLOW_UP_RESPONSE_SCHEMA,
            ),
            request_options={'timeout': 10},
        )
        questions = _extract_questions_from_text(getattr(response, "text", ""))
        if len(questions) >= 3:
            return questions[:3]
        raise GeminiResponseError("Gemini returned fewer than 3 follow-up questions.")
    except Exception as e:
        logger.error(f"generate_follow_up_questions error: {e}")
    return _fallback_follow_up_questions(candidate_text, context)


def analyze_interview(transcripts: list) -> dict:
    """
    Called once when the meeting ends.
    transcripts: list of dicts with keys speaker, text, start_time, end_time.
    Returns a dict matching the AIReport model fields, or {} on failure.
    """
    candidate_lines = [
        f"[{i + 1}] {seg['text']}"
        for i, seg in enumerate(transcripts)
        if seg.get('speaker') == 'candidate'
    ]

    if not candidate_lines:
        logger.warning("analyze_interview called with no candidate lines — skipping")
        return {}

    prompt = INTERVIEW_ANALYSIS_PROMPT.format(
        candidate_transcript="\n".join(candidate_lines)
    )

    last_error = None
    for model_name in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            model = get_gemini_client(model_name)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0,
                    max_output_tokens=2048,
                    response_mime_type="application/json",
                    response_schema=INTERVIEW_ANALYSIS_SCHEMA,
                ),
                request_options={'timeout': 30},
            )
            result = extract_json_object(response.text.strip())
            logger.info(f"Interview analysis complete — score: {result.get('fit_score')}, "
                        f"recommendation: {result.get('recommendation')}")
            return result
        except Exception as e:
            last_error = str(e)
            logger.warning(f"analyze_interview failed with {model_name}: {e}")

    logger.error(f"analyze_interview exhausted all models. Last error: {last_error}")
    return {}


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
    api_failure = False  

    primary_model = get_gemini_client(PRIMARY_MODEL)

    for attempt in range(max_retries):
        try:
            logger.info(f"Gemini API attempt {attempt + 1}/{max_retries} (model: {PRIMARY_MODEL})")
            result = _call_model(primary_model, prompt)
            logger.info(f"Gemini response received — fit_score: {result['fit_score']}")
            return result

        except (json.JSONDecodeError, GeminiResponseError) as e:
            last_error = str(e)
            api_failure = False
            logger.warning(f"Attempt {attempt + 1} failed (validation): {last_error}")

        except GeminiConfigurationError:
            raise

        except Exception as e:
            last_error = str(e)
            api_failure = True
            logger.warning(f"Attempt {attempt + 1} failed (API error): {last_error}")

        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)

    if api_failure:
        logger.warning(f"Primary model exhausted — falling back to {FALLBACK_MODEL}")
        try:
            fallback_model = get_gemini_client(FALLBACK_MODEL)
            result = _call_model(fallback_model, prompt)
            logger.info(f"Fallback model succeeded — fit_score: {result['fit_score']}")
            return result
        except Exception as e:
            last_error = str(e)
            logger.error(f"Fallback model also failed: {last_error}")

    raise GeminiResponseError(
        f"Gemini API failed after {max_retries} attempts. Last error: {last_error}"
    )

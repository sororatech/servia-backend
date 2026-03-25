from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.ai_reports.models import AIReport, TemporaryAIResponse
from apps.ai_reports.serializers import AIReportSerializer
from apps.candidate.models import Candidate
from apps.ai_reports.services.gemini_client import (
    GeminiConfigurationError,
    GeminiResponseError,
    analyze_cv,
)


@shared_task(bind=True, max_retries=3)
def analyze_cv_task(self, candidate_id: str, cv_text: str, job_description: str):
    """
    Background Celery task to analyze a candidate CV using Gemini Flash.
    """
    try:
        print(f"Starting CV analysis for candidate {candidate_id}")

        candidate = Candidate.objects.filter(id=candidate_id).first()
        if not candidate:
            raise ObjectDoesNotExist(f"Candidate {candidate_id} does not exist.")

        self.update_state(
            state='PROGRESS',
            meta={'candidate_id': candidate_id, 'status': 'Analyzing CV...'}
        )

        result = analyze_cv(
            cv_text=cv_text,
            job_description=job_description
        )

        self.update_state(
            state='PROGRESS',
            meta={'candidate_id': candidate_id, 'status': 'Validating AI response...'}
        )

        serializer = AIReportSerializer(data=result)
        serializer.is_valid(raise_exception=True)

        self.update_state(
            state='PROGRESS',
            meta={'candidate_id': candidate_id, 'status': 'Saving AI report...'}
        )

        with transaction.atomic():
            report = AIReport.objects.create(
                candidate=candidate,
                report_type=AIReport.ReportType.CV_SCREENING,
                raw_response=result,
                **serializer.validated_data,
            )

            candidate.ai_score = serializer.validated_data['fit_score']
            candidate.ai_summary = serializer.validated_data['summary']
            candidate.ai_strengths = serializer.validated_data['strengths']
            candidate.ai_weaknesses = serializer.validated_data['weaknesses']
            candidate.ai_feedback = serializer.validated_data['feedback']
            candidate.cv_status = Candidate.CVStatus.ANALYZED
            candidate.save(
                update_fields=[
                    'ai_score',
                    'ai_summary',
                    'ai_strengths',
                    'ai_weaknesses',
                    'ai_feedback',
                    'cv_status',
                    'updated_at',
                ]
            )

        print(f"CV analysis complete for candidate {candidate_id} — score: {result['fit_score']}")

        return {
            'candidate_id': candidate_id,
            'status': 'complete',
            'report_id': str(report.id),
            'result': serializer.validated_data,
        }

    except (ValidationError, GeminiResponseError, GeminiConfigurationError, ObjectDoesNotExist) as e:
        candidate = Candidate.objects.filter(id=candidate_id).first()
        if candidate:
            TemporaryAIResponse.objects.create(
                candidate=candidate,
                raw_response={
                    'error': str(e),
                    'candidate_id': candidate_id,
                },
            )
        self.update_state(
            state='FAILURE',
            meta={'candidate_id': candidate_id, 'status': 'failed', 'error': str(e)}
        )
        print(f"CV analysis failed validation/config for candidate {candidate_id}: {e}")
        raise

    except Exception as e:
        print(f"CV analysis failed for candidate {candidate_id}: {e}")
        raise self.retry(exc=e, countdown=60)

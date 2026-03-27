from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.ai_reports.models import AIReport, TemporaryAIResponse
from apps.ai_reports.serializers import AIReportSerializer
from apps.candidate.models import Candidate
from apps.users.tasks import send_cv_analyzed_email, send_rejected_cv_email, send_shortlisted_email
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

        if AIReport.objects.filter(
            candidate=candidate,
            report_type=AIReport.ReportType.CV_SCREENING,
        ).exists():
            print(f"AIReport already exists for candidate {candidate_id} — skipping duplicate analysis.")
            return {'candidate_id': candidate_id, 'status': 'skipped', 'reason': 'report_already_exists'}

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
            vd = serializer.validated_data
            report = AIReport.objects.create(
                candidate=candidate,
                report_type=AIReport.ReportType.CV_SCREENING,
                raw_response=result,
                fit_score=vd['fit_score'],
                summary=vd['summary'],
                strengths=vd['strengths'],
                weaknesses=vd['weaknesses'],
                feedback=vd['feedback'],
                extracted_skills=vd.get('extracted_skills') or [],
            )

            fit_score = serializer.validated_data['fit_score']
            candidate.ai_score = fit_score
            candidate.ai_summary = serializer.validated_data['summary']
            candidate.ai_strengths = serializer.validated_data['strengths']
            candidate.ai_weaknesses = serializer.validated_data['weaknesses']
            candidate.ai_skills = serializer.validated_data.get('extracted_skills', [])
            candidate.ai_feedback = serializer.validated_data['feedback']
            candidate.cv_status = Candidate.CVStatus.ANALYZED

            update_fields = [
                'ai_score', 'ai_summary', 'ai_strengths',
                'ai_weaknesses', 'ai_skills', 'ai_feedback', 'cv_status', 'updated_at',
            ]

            if fit_score >= 70:
                candidate.status = Candidate.Status.SHORTLISTED
                update_fields.append('status')
            elif fit_score < 40:
                candidate.status = Candidate.Status.REJECTED_CV
                update_fields.append('status')
            else:
                candidate.status = Candidate.Status.SCREENED  # Manual review
                update_fields.append('status')

            candidate.save(update_fields=update_fields)

        if candidate.status == Candidate.Status.SHORTLISTED:
            send_shortlisted_email.delay(candidate_id)
        elif candidate.status == Candidate.Status.REJECTED_CV:
            send_rejected_cv_email.delay(candidate_id)
        elif candidate.status == Candidate.Status.SCREENED:
            send_cv_analyzed_email.delay(candidate_id)
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
            candidate.cv_status = Candidate.CVStatus.ERROR
            candidate.save(update_fields=['cv_status'])
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
        if self.request.retries >= self.max_retries:
            candidate = Candidate.objects.filter(id=candidate_id).first()
            if candidate:
                candidate.cv_status = Candidate.CVStatus.ERROR
                candidate.save(update_fields=['cv_status'])
        raise self.retry(exc=e, countdown=60)

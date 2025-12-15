from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import os
import re
import logging

from .models import CVUpload
from .forms import CVUploadForm
from .parser import CVParser
from .cv_scorer import CVScorer
from utiliy.suggestions import generate_resume_suggestions

logger = logging.getLogger(__name__)


def home(request):
    return render(request, "analyzer/index.html")


@login_required
def upload(request):
    """Bulk CV upload for matching"""
    if request.method == "POST":
        form = CVUploadForm(request.POST, request.FILES)
        files = request.FILES.getlist("cv_files")

        if form.is_valid():
            required_experience = form.cleaned_data.get('required_experience')
            required_education = (form.cleaned_data.get('required_education') or '').lower()
            required_skills = [
                s.strip().lower()
                for s in form.cleaned_data.get('required_skills', '').split(',')
                if s.strip()
            ]

            # Clear previous CVs for this user
            CVUpload.objects.filter(user=request.user).delete()

            uploaded_cvs = []
            parser = CVParser()
            scorer = CVScorer()

            for file in files:
                file_ext = os.path.splitext(file.name)[1].lower()
                if file.size > 5 * 1024 * 1024:
                    messages.error(request, f"File too large (max 5MB): {file.name}")
                    continue

                cv_upload = CVUpload(user=request.user, file=file, target_job_role=form.cleaned_data.get('job_name', ''))
                cv_upload.save()

                try:
                    # Read file from storage (Render-safe)
                    with default_storage.open(cv_upload.file.name, 'rb') as f:
                        parsed_data = parser.parse_cv(f, file_ext)

                    scoring_results = scorer.score_cv(parsed_data)

                    # Save parsed content
                    cv_upload.raw_text = parsed_data.get("raw_text", '') or ''
                    cv_upload.experience = parsed_data.get("experience", '') or ''
                    cv_upload.education = parsed_data.get("education", '') or ''
                    cv_upload.skills = parsed_data.get("skills", '') or ''

                    # Save scores
                    scores = scoring_results.get("section_scores", {})
                    cv_upload.overall_score = scoring_results.get("overall_score", 0) or 0
                    cv_upload.contact_score = scores.get("contact", 0) or 0
                    cv_upload.experience_score = scores.get("experience", 0) or 0
                    cv_upload.education_score = scores.get("education", 0) or 0
                    cv_upload.skills_score = scores.get("skills", 0) or 0
                    cv_upload.format_score = scores.get("format", 0) or 0

                    # Calculate matching score
                    matching_score = 0
                    total_criteria = 0

                    # Experience
                    if required_experience:
                        total_criteria += 1
                        exp_years = 0
                        try:
                            # Extract year ranges like 2019-2022
                            for start_str, end_str in re.findall(r'(\d{4})\s*[-–]\s*(\d{4})', cv_upload.experience):
                                exp_years += max(0, int(end_str) - int(start_str))
                            if exp_years == 0:
                                years = [int(s) for s in re.findall(r'\b(19|20)\d{2}\b', cv_upload.experience)]
                                if years:
                                    exp_years = max(years) - min(years)
                        except Exception:
                            exp_years = 0
                        if exp_years >= int(required_experience):
                            matching_score += 1

                    # Education
                    if required_education:
                        total_criteria += 1
                        if required_education in (cv_upload.education or '').lower():
                            matching_score += 1

                    # Skills
                    if required_skills:
                        total_criteria += 1
                        cv_skills = [s.strip().lower() for s in re.split(r',|;', cv_upload.skills or '') if s.strip()]
                        if cv_skills:
                            matched_skills = set(required_skills) & set(cv_skills)
                            skill_ratio = len(matched_skills) / len(required_skills)
                            matching_score += skill_ratio

                    cv_upload.matching_score = round((matching_score / total_criteria) * 100, 2) if total_criteria else 0
                    cv_upload.processed = True
                    cv_upload.save()
                    uploaded_cvs.append(cv_upload)

                except Exception as e:
                    logger.error(f"Error processing {file.name}: {e}")
                    messages.error(request, f"Error processing {file.name}: {str(e)}")
                    if cv_upload.pk:
                        if cv_upload.file and default_storage.exists(cv_upload.file.name):
                            default_storage.delete(cv_upload.file.name)
                        cv_upload.delete()

            if not uploaded_cvs:
                messages.error(request, "No valid files were processed.")
                return redirect('upload')

            # Sort by matching score
            matched_cvs = sorted(uploaded_cvs, key=lambda x: x.matching_score, reverse=True)
            request.session["matched_cv_ids"] = [cv.id for cv in matched_cvs]
            request.session["job_title"] = form.cleaned_data.get('job_name', '')
            return redirect("matched_results")

    else:
        form = CVUploadForm()

    return render(request, "analyzer/upload.html", {"form": form})


@login_required
def matched_results(request):
    matched_ids = request.session.get("matched_cv_ids", [])
    if not matched_ids:
        return render(request, "analyzer/matched_results.html", {
            "cvs": [],
            "job_title": request.session.get("job_title", ""),
            "error_message": "No CVs have been uploaded or matched yet."
        })

    cvs = CVUpload.objects.filter(id__in=matched_ids, processed=True).order_by('-matching_score')
    request.session["matched_cv_ids"] = list(cvs.values_list('id', flat=True))
    job_title = request.session.get("job_title", "")

    return render(request, "analyzer/matched_results.html", {
        "cvs": cvs,
        "job_title": job_title,
        "error_message": None
    })


@login_required
def upload_and_suggest(request):
    if request.method == "POST":
        file = request.FILES.get("file")
        job_name = (request.POST.get("job_name") or "").strip()

        if not file:
            messages.error(request, "No CV file uploaded.")
            return render(request, "analyzer/upload_and_suggest.html")
        if not job_name:
            messages.error(request, "Please specify a job title for suggestions.")
            return render(request, "analyzer/upload_and_suggest.html")

        file_ext = os.path.splitext(file.name)[1].lower()
        allowed_exts = ['.pdf', '.doc', '.docx', '.txt']
        max_size = 5 * 1024 * 1024

        if file_ext not in allowed_exts:
            messages.error(request, f"Unsupported file format: {file_ext}")
            return render(request, "analyzer/upload_and_suggest.html")
        if file.size > max_size:
            messages.error(request, "File size exceeds 5MB limit.")
            return render(request, "analyzer/upload_and_suggest.html")

        cv_upload = CVUpload(user=request.user, file=file, target_job_role=job_name)
        cv_upload.save()

        try:
            parser = CVParser()
            scorer = CVScorer()

            with default_storage.open(cv_upload.file.name, 'rb') as f:
                parsed_data = parser.parse_cv(f, file_ext)

            scoring_results = scorer.score_cv(parsed_data)

            # Save parsed data
            cv_upload.raw_text = parsed_data.get('raw_text', '') or ''
            cv_upload.contact_info = parsed_data.get('contact_info', '') or ''
            cv_upload.experience = parsed_data.get('experience', '') or ''
            cv_upload.education = parsed_data.get('education', '') or ''
            cv_upload.skills = parsed_data.get('skills', '') or ''

            # Save scores
            scores = scoring_results.get('section_scores', {})
            cv_upload.overall_score = scoring_results.get('overall_score', 0) or 0
            cv_upload.contact_score = scores.get("contact", 0) or 0
            cv_upload.experience_score = scores.get("experience", 0) or 0
            cv_upload.education_score = scores.get("education", 0) or 0
            cv_upload.skills_score = scores.get("skills", 0) or 0
            cv_upload.format_score = scores.get("format", 0) or 0

            # Generate suggestions safely
            resume_text = cv_upload.raw_text
            try:
                job_suggestions = generate_resume_suggestions(resume_text, job_name)
            except Exception:
                job_suggestions = ""

            default_suggestions_list = scoring_results.get('suggestions', [])
            default_suggestions = "\n".join(default_suggestions_list) if isinstance(default_suggestions_list, list) else str(default_suggestions_list or "")

            # Combine AI and default suggestions
            final_suggestions = ""
            if job_suggestions and len(job_suggestions.strip()) > 50:
                final_suggestions = job_suggestions
                ai_lines = [line.strip().lower() for line in job_suggestions.split('\n') if line.strip()]
                default_lines = [line.strip() for line in default_suggestions.split('\n') if line.strip()]
                unique_defaults = [line for line in default_lines if not any(line.lower() in ai_line or ai_line in line.lower() for ai_line in ai_lines)]
                if unique_defaults:
                    final_suggestions += "\n\nAdditional improvements:\n• " + "\n• ".join(unique_defaults)
            else:
                final_suggestions = f"For the {job_name} role:\n• " + default_suggestions.replace("\n", "\n• ")

            cv_upload.suggestions = final_suggestions[:1500]
            cv_upload.processed = True
            cv_upload.save()

            return render(request, "analyzer/cv_suggestions.html", {"cv": cv_upload})

        except Exception as e:
            logger.error(f"Error processing CV: {e}")
            if cv_upload.pk:
                if cv_upload.file and default_storage.exists(cv_upload.file.name):
                    default_storage.delete(cv_upload.file.name)
                cv_upload.delete()
            messages.error(request, f"Error processing file: {str(e)}")
            return render(request, "analyzer/upload_and_suggest.html")

    return render(request, "analyzer/upload_and_suggest.html")


@login_required
def cv_suggestions(request, cv_id):
    cv = get_object_or_404(CVUpload, id=cv_id, user=request.user, processed=True)
    suggestions = (cv.suggestions or "").strip()
    return render(request, "analyzer/cv_suggestions.html", {"cv": cv, "suggestions": suggestions[:2000]})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def api_delete_cv(request, cv_id):
    cv = get_object_or_404(CVUpload, id=cv_id, user=request.user)
    if cv.file and default_storage.exists(cv.file.name):
        default_storage.delete(cv.file.name)
    cv.delete()
    return Response({"message": "CV deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

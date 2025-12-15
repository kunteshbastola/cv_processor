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
from utiliy.suggestions import generate_job_keyword_suggestions


logger = logging.getLogger(__name__)


def home(request):
    return render(request, "analyzer/index.html")


@login_required
def upload(request):
    """Bulk CV upload for matching"""
    if request.method == "POST":
        form = CVUploadForm(request.POST, request.FILES)
        files = request.FILES.getlist("cv_files")

        job_name = (request.POST.get("job_name") or "").strip()

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
                    
                    parsed_data = parser.parse_cv(cv_upload.file, file_ext)


                    scoring_results = scorer.score_cv(parsed_data, job_name)


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
    suggestions = []  # initialize
    if request.method == "POST":
        file = request.FILES.get("file")
        job_name = (request.POST.get("job_name") or "").strip()

        if not file or not job_name:
            messages.error(request, "Please upload a CV and specify a job title.")
            return render(request, "analyzer/upload_and_suggest.html")

        file_ext = os.path.splitext(file.name)[1].lower()
        if file_ext not in ['.pdf', '.doc', '.docx', '.txt']:
            messages.error(request, "Unsupported file format.")
            return render(request, "analyzer/upload_and_suggest.html")

        # Save uploaded CV
        cv_upload = CVUpload(user=request.user, file=file, target_job_role=job_name)
        cv_upload.save()

        try:
            parser = CVParser()
            scorer = CVScorer()

            # Pass the actual file path to the parser
            file_path = cv_upload.file.path
            parsed_data = parser.parse_cv(file_path, file_ext)

            # Generate job-specific suggestions
            suggestions = generate_job_keyword_suggestions(parsed_data.get("raw_text", ""), job_name)

            # Save CV info
            cv_upload.raw_text = parsed_data.get("raw_text", "")
            cv_upload.processed = True
            cv_upload.suggestions = "\n".join(suggestions)
            cv_upload.save()

        except Exception as e:
            messages.error(request, f"Error processing CV: {e}")

    return render(request, "analyzer/upload_and_suggest.html", {"suggestions": suggestions})




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

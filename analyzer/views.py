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

from .models import CVUpload
from .forms import CVUploadForm
from .parser import CVParser
from .cv_scorer import CVScorer
from utiliy.suggestions import generate_resume_suggestions


def home(request):
    return render(request, "analyzer/index.html")


@login_required
def upload(request):
    if request.method == "POST":
        form = CVUploadForm(request.POST, request.FILES)
        files = request.FILES.getlist("cv_files")

        if form.is_valid():
            required_experience = form.cleaned_data.get('required_experience')
            required_education = form.cleaned_data.get('required_education', '').lower()
            required_skills = [
                skill.strip().lower()
                for skill in form.cleaned_data.get('required_skills', '').split(',')
                if skill.strip()
            ]

            # Clear previous CV uploads for this user
            CVUpload.objects.filter(user=request.user).delete()

            uploaded_cvs = []
            parser = CVParser()
            scorer = CVScorer()

            for file in files:
                file_ext = os.path.splitext(file.name)[1].lower()
                if file.size > 5 * 1024 * 1024:
                    messages.error(request, f"File too large (max 5MB): {file.name}")
                    continue

                cv_upload = CVUpload(
                    user=request.user,
                    file=file,
                    target_job_role=form.cleaned_data.get('job_name', '')
                )
                cv_upload.save()

                try:
                    parsed_data = parser.parse_cv(cv_upload.file.path, file_ext)
                    scoring_results = scorer.score_cv(parsed_data)

                    # Save parsed fields
                    cv_upload.raw_text = parsed_data.get("raw_text", "")
                    cv_upload.experience = parsed_data.get("experience", "")
                    cv_upload.education = parsed_data.get("education", "")
                    cv_upload.skills = parsed_data.get("skills", "")

                    # Save scores
                    scores = scoring_results.get("scores", {})
                    cv_upload.overall_score = scoring_results.get("overall_score", 0) or 0
                    cv_upload.contact_score = scores.get("contact", 0) or 0
                    cv_upload.experience_score = scores.get("experience", 0) or 0
                    cv_upload.education_score = scores.get("education", 0) or 0
                    cv_upload.skills_score = scores.get("skills", 0) or 0
                    cv_upload.format_score = scores.get("format", 0) or 0

                    # ===============================
                    # Matching score logic
                    # ===============================
                    matching_score = 0
                    total_criteria = 0

                    # Experience
                    if required_experience:
                        total_criteria += 1
                        exp_text = cv_upload.experience or ""
                        exp_years = 0
                        try:
                            # Check year ranges like 2019-2022
                            for start_str, end_str in re.findall(r'(\d{4})\s*[-–]\s*(\d{4})', exp_text):
                                start, end = int(start_str), int(end_str)
                                exp_years += max(0, end - start)
                            if exp_years == 0:
                                years = [int(s) for s in re.findall(r'\b(19|20)\d{2}\b', exp_text)]
                                if years:
                                    exp_years = max(years) - min(years)
                        except Exception:
                            exp_years = 0

                        if exp_years >= int(required_experience):
                            matching_score += 1

                    # Education
                    if required_education:
                        total_criteria += 1
                        if required_education in (cv_upload.education or "").lower():
                            matching_score += 1

                    # Skills
                    if required_skills:
                        total_criteria += 1
                        cv_skills = [
                            s.strip().lower()
                            for s in re.split(r',|;', cv_upload.skills or "")
                            if s.strip()
                        ]
                        if cv_skills:
                            matched_skills = set(required_skills) & set(cv_skills)
                            skill_ratio = len(matched_skills) / len(required_skills)
                            matching_score += skill_ratio

                    cv_upload.matching_score = round((matching_score / total_criteria) * 100, 2) if total_criteria else 0
                    cv_upload.processed = True
                    cv_upload.save()
                    uploaded_cvs.append(cv_upload)

                except Exception as e:
                    messages.error(request, f"Error processing {file.name}: {str(e)}")
                    cv_upload.file.delete(save=False)
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
        job_name = request.POST.get("job_name", "")

        if not file:
            messages.error(request, "No CV file uploaded.")
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
            parsed_data = parser.parse_cv(cv_upload.file.path, file_ext)
            scoring_results = scorer.score_cv(parsed_data)

            # Save parsed data
            cv_upload.raw_text = parsed_data.get('raw_text', '') or ''
            cv_upload.contact_info = parsed_data.get('contact_info', '') or ''
            cv_upload.experience = parsed_data.get('experience', '') or ''
            cv_upload.education = parsed_data.get('education', '') or ''
            cv_upload.skills = parsed_data.get('skills', '') or ''

            # Save scores
            scores = scoring_results.get('scores', {})
            cv_upload.overall_score = scoring_results.get('overall_score', 0) or 0
            cv_upload.contact_score = scores.get('contact', 0) or 0
            cv_upload.experience_score = scores.get('experience', 0) or 0
            cv_upload.education_score = scores.get('education', 0) or 0
            cv_upload.skills_score = scores.get('skills', 0) or 0
            cv_upload.format_score = scores.get('format', 0) or 0

            # Generate suggestions
            resume_text = parsed_data.get('raw_text', '') or ''
            job_suggestions = generate_resume_suggestions(resume_text, job_name)
            existing_suggestions = "\n".join(scoring_results.get('suggestions', [])) if isinstance(scoring_results.get('suggestions', []), list) else str(scoring_results.get('suggestions', ''))
            combined_suggestions = f"{existing_suggestions}\n{job_suggestions}".strip()
            cv_upload.suggestions = combined_suggestions[:1000]  # limit length

            cv_upload.processed = True
            cv_upload.save()

            return render(request, "analyzer/cv_suggestions.html", {"cv": cv_upload})

        except Exception as e:
            cv_upload.file.delete(save=False)
            cv_upload.delete()
            messages.error(request, f"Error processing file: {str(e)}")
            return render(request, "analyzer/upload_and_suggest.html")

    return render(request, "analyzer/upload_and_suggest.html")


@login_required
def cv_suggestions(request, cv_id):
    cv = get_object_or_404(CVUpload, id=cv_id, user=request.user, processed=True)
    safe_suggestions = (cv.suggestions or "").strip()
    if len(safe_suggestions) > 1000:
        safe_suggestions = safe_suggestions[:1000] + "..."

    return render(request, "analyzer/cv_suggestions.html", {
        "cv": cv,
        "suggestions": safe_suggestions,
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def api_delete_cv(request, cv_id):
    cv = get_object_or_404(CVUpload, id=cv_id, user=request.user)

    # Delete file safely
    if cv.file and default_storage.exists(cv.file.name):
        default_storage.delete(cv.file.name)

    cv.delete()
    return Response({"message": "CV deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# @parser_classes([MultiPartParser])
# def api_upload(request): # This API endpoint allows users to upload multiple CV files for analysis.
#     """
#     API endpoint for uploading and analyzing CVs
#     Accepts multiple files with 'files[]' parameter
#     Returns analysis results including scores and suggestions
#     """
#     if 'files[]' not in request.FILES:
#         return Response(
#             {'error': 'No files provided. Use "files[]" parameter.'},
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     files = request.FILES.getlist('files[]')
#     job_name = request.data.get('job_name', '')
#     results = []
#     parser = CVParser()
#     scorer = CVScorer()

#     for file in files:
#         file_data = {
#             'filename': file.name,
#             'error': None,
#             'status': 'success'
#         }

#         try:
#             # Validate file
#             file_ext = os.path.splitext(file.name)[1].lower()
#             if file_ext not in ['.pdf', '.doc', '.docx', '.txt']:
#                 raise ValueError(f"Unsupported file format: {file_ext}")

#             if file.size > 5 * 1024 * 1024:  # 5MB limit
#                 raise ValueError("File size exceeds 5MB limit")

#             # Create and save CVUpload instance
#             cv_upload = CVUpload(
#                 user=request.user,
#                 file=file,
#                 filename=file.name,
#                 job_name=job_name
#             )
#             cv_upload.save()

#             # Process the CV
#             file_path = default_storage.path(cv_upload.file.name)
#             parsed_data = parser.parse_cv(file_path, file_ext)
#             scoring_results = scorer.score_cv(parsed_data)

#             # Update CVUpload with analysis results
#             cv_upload.raw_text = parsed_data.get('raw_text', '')
#             cv_upload.contact_info = parsed_data.get('contact_info', '')
#             cv_upload.experience = parsed_data.get('experience', '')
#             cv_upload.education = parsed_data.get('education', '')
#             cv_upload.skills = parsed_data.get('skills', '')

#             scores = scoring_results.get('scores', {})
#             cv_upload.overall_score = scoring_results.get('overall_score', 0)
#             cv_upload.contact_score = scores.get('contact', 0)
#             cv_upload.experience_score = scores.get('experience', 0)
#             cv_upload.education_score = scores.get('education', 0)
#             cv_upload.skills_score = scores.get('skills', 0)
#             cv_upload.format_score = scores.get('format', 0)

#             # Generate suggestions
#             resume_text = parsed_data.get('raw_text', '')
#             job_suggestions = generate_resume_suggestions(resume_text, job_name)
#             existing_suggestions = scoring_results.get('suggestions', '')
#             cv_upload.suggestions = f"{existing_suggestions}\n{job_suggestions}".strip()
            
#             cv_upload.processed = True
#             cv_upload.save()

#             # Prepare response data
#             file_data.update({
#                 'id': cv_upload.id,
#                 'overall_score': cv_upload.overall_score,
#                 'scores': {
#                     'contact': cv_upload.contact_score,
#                     'experience': cv_upload.experience_score,
#                     'education': cv_upload.education_score,
#                     'skills': cv_upload.skills_score,
#                     'format': cv_upload.format_score,
#                 },
#                 'suggestions': cv_upload.suggestions,
#                 'processed_at': cv_upload.uploaded_at
#             })

#         except Exception as e:
#             file_data.update({
#                 'error': str(e),
#                 'status': 'failed'
#             })
#             # Clean up if file was saved but processing failed
#             if 'cv_upload' in locals() and cv_upload.pk:
#                 cv_upload.file.delete(save=False)
#                 cv_upload.delete()

#         results.append(file_data)

#     return Response({
#         'count': len(results),
#         'success_count': len([r for r in results if r['status'] == 'success']),
#         'results': results
#     })

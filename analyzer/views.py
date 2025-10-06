# Create your views here.
from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from .models import CVUpload
from .forms import CVUploadForm
from .parser import CVParser
from .cv_scorer import CVScorer
from .serializers import CVUploadSerializer
import os
from django.core.paginator import Paginator
from rest_framework.decorators import api_view, parser_classes,permission_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from rest_framework.permissions import IsAuthenticated
# Fix your import path as per your folder structure:
from utiliy.suggestions import generate_resume_suggestions
from django.contrib.auth.decorators import login_required









@login_required
def upload_cv(request):
    if request.method == "POST":
        form = CVUploadForm(request.POST, request.FILES)
        files = request.FILES.getlist("cv_files")

        if form.is_valid():
            try:
                form.validate_multiple_files(files)
            except forms.ValidationError as ve:
                for error in ve.error_list:
                    messages.error(request, error)
                return render(request, "analyzer/upload.html", {"form": form})

            # Extract job and matching requirements
            job_name = form.cleaned_data['job_name']
            required_experience = form.cleaned_data.get('required_experience')
            required_education = form.cleaned_data.get('required_education', '').lower()
            required_skills = [
                skill.strip().lower() for skill in form.cleaned_data.get('required_skills', '').split(',')
                if skill.strip()
            ]

            action = request.POST.get("action")  # e.g., "suggestions", "top5", "match"

            # Clear old uploads
            CVUpload.objects.filter(user=request.user).delete()

            uploaded_cvs = []
            parser = CVParser()
            scorer = CVScorer()

            for file in files:
                file_ext = os.path.splitext(file.name)[1].lower()
                if file.size > 5 * 1024 * 1024:
                    messages.error(request, f"File too large (max 5MB): {file.name}")
                    continue

                cv_upload = CVUpload(file=file, filename=file.name, user=request.user)
                cv_upload.save()

                try:
                    file_path = cv_upload.file.path
                    parsed_data = parser.parse_cv(file_path, file_ext)
                    scoring_results = scorer.score_cv(parsed_data)

                    # Save parsed fields
                    cv_upload.raw_text = parsed_data.get("raw_text", "")
                    cv_upload.contact_info = parsed_data.get("contact_info", "")
                    cv_upload.experience = parsed_data.get("experience", "")
                    cv_upload.education = parsed_data.get("education", "")
                    cv_upload.skills = parsed_data.get("skills", "")

                    # Save scores
                    scores = scoring_results.get("scores", {})
                    cv_upload.overall_score = scoring_results.get("overall_score", 0)
                    cv_upload.contact_score = scores.get("contact", 0)
                    cv_upload.experience_score = scores.get("experience", 0)
                    cv_upload.education_score = scores.get("education", 0)
                    cv_upload.skills_score = scores.get("skills", 0)
                    cv_upload.format_score = scores.get("format", 0)

                    # Generate suggestions
                    resume_text = parsed_data.get("raw_text", "")
                    job_suggestions = generate_resume_suggestions(resume_text, job_name)
                    existing_suggestions = scoring_results.get("suggestions", "")
                    combined_suggestions = f"{existing_suggestions}\n{job_suggestions}".strip()
                    cv_upload.suggestions = combined_suggestions

                    # Add job name
                    cv_upload.job_name = job_name
                    cv_upload.processed = True

                    # ===============================
                    # ✨ Matching Score Logic ✨
                    # ===============================
                    matching_score = 0
                    total_criteria = 0

                    # Experience (you can enhance with NLP later)
                    if required_experience:
                        total_criteria += 1
                        if str(required_experience) in cv_upload.experience:
                            matching_score += 1

                    # Education
                    if required_education:
                        total_criteria += 1
                        if required_education in cv_upload.education.lower():
                            matching_score += 1

                    # Skills
                    if required_skills:
                        total_criteria += 1
                        cv_skills = [s.strip().lower() for s in cv_upload.skills.split(',')]
                        matched_skills = len(set(required_skills) & set(cv_skills))
                        if matched_skills >= len(required_skills) * 0.6:  # 60% match
                            matching_score += 1

                    # Final matching score as percentage
                    if total_criteria > 0:
                        cv_upload.matching_score = round((matching_score / total_criteria) * 100, 2)
                    else:
                        cv_upload.matching_score = None

                    cv_upload.save()
                    uploaded_cvs.append(cv_upload)

                except Exception as e:
                    messages.error(request, f"Error processing {file.name}: {str(e)}")
                    cv_upload.delete()

            if not uploaded_cvs:
                messages.error(request, "No valid files were processed.")
                return redirect('upload_cv')

            # Process according to action
            if action == "suggestions":
                request.session["uploaded_cv_ids"] = [cv.id for cv in uploaded_cvs]
                return redirect("results")

            elif action == "top5":
                top_cvs = sorted(uploaded_cvs, key=lambda x: x.overall_score or 0, reverse=True)[:5]
                request.session["top_cv_ids"] = [cv.id for cv in top_cvs]
                messages.success(request, f"Processed {len(uploaded_cvs)} CV(s). Showing top 5 results.")
                return redirect("cv_rank")

            elif action == "match":
                matched_cvs = sorted(
                    [cv for cv in uploaded_cvs if cv.matching_score is not None],
                    key=lambda x: x.matching_score,
                    reverse=True
                )
                request.session["matched_cv_ids"] = [cv.id for cv in matched_cvs]
                return redirect("matched_results")

    else:
        form = CVUploadForm()

    return render(request, "analyzer/upload.html", {"form": form})



# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def api_cv_rank(request):
#     top_cvs = CVUpload.objects.filter(processed=True).order_by('-overall_score')[:5]
#     serializer = CVUploadSerializer(top_cvs, many=True)
#     return Response(serializer.data)



from rest_framework.pagination import PageNumberPagination


def home(request):
    return render(request, "analyzer/home.html")

@login_required
def matched_results(request):
    matched_ids = request.session.get("matched_cv_ids", [])
    cvs = CVUpload.objects.filter(id__in=matched_ids)

    if not cvs.exists():
        messages.warning(request, "No CVs matched your criteria.")
        return render(request, "analyzer/matched_results.html", {"best_cv": None})

    # Pick the single best CV (highest matching_score)
    best_cv = max(cvs, key=lambda x: x.matching_score or 0)

    return render(request, "analyzer/matched_results.html", {"best_cv": best_cv})




from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib import messages

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
        max_size = 5 * 1024 * 1024  # 5MB
        
        if file_ext not in allowed_exts:
            messages.error(request, f"Unsupported file format: {file_ext}")
            return render(request, "analyzer/upload_and_suggest.html")

        if file.size > max_size:
            messages.error(request, "File size exceeds 5MB limit.")
            return render(request, "analyzer/upload_and_suggest.html")

        cv_upload = CVUpload(user=request.user, file=file, filename=file.name, job_name=job_name)
        cv_upload.save()

        try:
            parser = CVParser()
            scorer = CVScorer()
            parsed_data = parser.parse_cv(cv_upload.file.path, file_ext)
            scoring_results = scorer.score_cv(parsed_data)

            cv_upload.raw_text = parsed_data.get('raw_text', '')
            cv_upload.contact_info = parsed_data.get('contact_info', '')
            cv_upload.experience = parsed_data.get('experience', '')
            cv_upload.education = parsed_data.get('education', '')
            cv_upload.skills = parsed_data.get('skills', '')

            scores = scoring_results.get('scores', {})
            cv_upload.overall_score = scoring_results.get('overall_score', 0)
            cv_upload.contact_score = scores.get('contact', 0)
            cv_upload.experience_score = scores.get('experience', 0)
            cv_upload.education_score = scores.get('education', 0)
            cv_upload.skills_score = scores.get('skills', 0)
            cv_upload.format_score = scores.get('format', 0)

            resume_text = parsed_data.get('raw_text', '')
            job_suggestions = generate_resume_suggestions(resume_text, job_name)
            existing_suggestions = scoring_results.get('suggestions', '')
            combined_suggestions = f"{existing_suggestions}\n{job_suggestions}".strip()

            cv_upload.suggestions = combined_suggestions
            cv_upload.processed = True
            cv_upload.save()

            # Pass cv_upload to template to show results
            return render(request, "analyzer/upload_and_suggest_results.html", {"cv": cv_upload})

        except Exception as e:
            cv_upload.file.delete(save=False)
            cv_upload.delete()
            messages.error(request, f"Error processing file: {str(e)}")
            return render(request, "analyzer/upload_and_suggest.html")

    # GET method, show upload form
    return render(request, "analyzer/upload_and_suggest.html")


 # This view displays the details of a specific CV including its scores and suggestions.


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

@login_required
def cv_suggestions(request, cv_id):
    cv = get_object_or_404(CVUpload, id=cv_id, user=request.user, processed=True)
    
    context = {
        "cv": cv,
    }
    return render(request, "analyzer/cv_suggestions.html", context)


# This view handles the deletion of a CV and its associated file.

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def api_delete_cv(request, cv_id):
    cv = get_object_or_404(CVUpload, id=cv_id, user=request.user)
    
    # Delete file from storage
    if cv.file:
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

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
def upload_cv(request): # it is the function to handle the CV upload and processing .so we can upload the CV and process it for scoring and suggestions.
    if request.method == "POST":
        print(">>> Received POST")
        form = CVUploadForm(request.POST, request.FILES)
        files = request.FILES.getlist("cv_files")
        print(">>> Files received:", files)

        if form.is_valid():
            try:
                form.validate_multiple_files(files)
            except forms.ValidationError as ve:
                for error in ve.error_list:
                    messages.error(request, error)
                return render(request, "analyzer/upload.html", {"form": form})

            job_name = form.cleaned_data['job_name']
            action = request.POST.get("action")

            CVUpload.objects.filter(user=request.user).delete()

            uploaded_cvs = []
            parser = CVParser()
            scorer = CVScorer()

            for file in files:
                file_ext = os.path.splitext(file.name)[1].lower()
                print(">>> Processing:", file.name)
                print(">>> Size:", file.size)

                if file.size > 5 * 1024 * 1024:
                    messages.error(request, f"File too large (max 5MB): {file.name}")
                    continue

                cv_upload = CVUpload(file=file, filename=file.name, user=request.user)
                cv_upload.save()

                try:
                    file_path = cv_upload.file.path
                    parsed_data = parser.parse_cv(file_path, file_ext)
                    scoring_results = scorer.score_cv(parsed_data)

                    cv_upload.raw_text = parsed_data.get("raw_text", "")
                    cv_upload.contact_info = parsed_data.get("contact_info", "")
                    cv_upload.experience = parsed_data.get("experience", "")
                    cv_upload.education = parsed_data.get("education", "")
                    cv_upload.skills = parsed_data.get("skills", "")

                    scores = scoring_results.get("scores", {})
                    cv_upload.overall_score = scoring_results.get("overall_score", 0)
                    cv_upload.contact_score = scores.get("contact", 0)
                    cv_upload.experience_score = scores.get("experience", 0)
                    cv_upload.education_score = scores.get("education", 0)
                    cv_upload.skills_score = scores.get("skills", 0)
                    cv_upload.format_score = scores.get("format", 0)

                    resume_text = parsed_data.get("raw_text", "")
                    job_suggestions = generate_resume_suggestions(resume_text, job_name)
                    existing_suggestions = scoring_results.get("suggestions", "")
                    combined_suggestions = f"{existing_suggestions}\n{job_suggestions}".strip()

                    cv_upload.suggestions = combined_suggestions
                    cv_upload.job_name = job_name
                    cv_upload.processed = True
                    cv_upload.save()

                    uploaded_cvs.append(cv_upload)

                except Exception as e:
                    messages.error(request, f"Error processing {file.name}: {str(e)}")
                    cv_upload.delete()

            if not uploaded_cvs:
                messages.error(request, "No valid files were processed.")
                return redirect('upload_cv')

            if action == "suggestions":
                request.session["uploaded_cv_ids"] = [cv.id for cv in uploaded_cvs]
                return redirect("results")

            elif action == "top5":
                top_cvs = sorted(uploaded_cvs, key=lambda x: x.overall_score or 0, reverse=True)[:5]
                request.session["top_cv_ids"] = [cv.id for cv in top_cvs]
                messages.success(request, f"Successfully processed {len(uploaded_cvs)} CV(s). Showing top 5 results.")
                return redirect("cv_rank")
    
    # Handle GET requests
    else:
        form = CVUploadForm()

    #  Always return something
    return render(request, "analyzer/upload.html", {"form": form})


@login_required
def cv_rank(request): # This view displays the top 5 CVs based on their overall score and  it also allows recuritment team to see the top CVs and the cv 
    # details of the CVs.
    top_cvs = CVUpload.objects.filter(processed=True).order_by('-overall_score')[:5]
    return render(request, "analyzer/cv_rank.html", {"cvs": top_cvs})



def results(request): # This view is used to diaplay the results of the cvs that have been processed and uploaded by the user.
    cvs = CVUpload.objects.filter(processed=True).order_by('-uploaded_at')
    
    
    # Pagination (we'll set 10 CVs per page)
    paginator = Paginator(cvs, 10)  # 10 CVs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "analyzer/results.html", {"page_obj": page_obj})
    


@login_required
def cv_detail(request, cv_id): # This view displays the details of a specific CV including its scores and suggestions.
    cv = get_object_or_404(CVUpload, id=cv_id, processed=True)
    return render(request, "analyzer/cv_detail.html", {"cv": cv})

@login_required
def delete_cv(request, cv_id): # This view handles the deletion of a CV and its associated file.
    if request.method == "POST":
        cv = get_object_or_404(CVUpload, id=cv_id)

        # Delete the file from storage
        if cv.file:
            default_storage.delete(cv.file.name)

        cv.delete()
        messages.success(request, "CV deleted successfully.")

    return redirect("results")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser])
def api_upload(request): # This API endpoint allows users to upload multiple CV files for analysis.
    """
    API endpoint for uploading and analyzing CVs
    Accepts multiple files with 'files[]' parameter
    Returns analysis results including scores and suggestions
    """
    if 'files[]' not in request.FILES:
        return Response(
            {'error': 'No files provided. Use "files[]" parameter.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    files = request.FILES.getlist('files[]')
    job_name = request.data.get('job_name', '')
    results = []
    parser = CVParser()
    scorer = CVScorer()

    for file in files:
        file_data = {
            'filename': file.name,
            'error': None,
            'status': 'success'
        }

        try:
            # Validate file
            file_ext = os.path.splitext(file.name)[1].lower()
            if file_ext not in ['.pdf', '.doc', '.docx', '.txt']:
                raise ValueError(f"Unsupported file format: {file_ext}")

            if file.size > 5 * 1024 * 1024:  # 5MB limit
                raise ValueError("File size exceeds 5MB limit")

            # Create and save CVUpload instance
            cv_upload = CVUpload(
                user=request.user,
                file=file,
                filename=file.name,
                job_name=job_name
            )
            cv_upload.save()

            # Process the CV
            file_path = default_storage.path(cv_upload.file.name)
            parsed_data = parser.parse_cv(file_path, file_ext)
            scoring_results = scorer.score_cv(parsed_data)

            # Update CVUpload with analysis results
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

            # Generate suggestions
            resume_text = parsed_data.get('raw_text', '')
            job_suggestions = generate_resume_suggestions(resume_text, job_name)
            existing_suggestions = scoring_results.get('suggestions', '')
            cv_upload.suggestions = f"{existing_suggestions}\n{job_suggestions}".strip()
            
            cv_upload.processed = True
            cv_upload.save()

            # Prepare response data
            file_data.update({
                'id': cv_upload.id,
                'overall_score': cv_upload.overall_score,
                'scores': {
                    'contact': cv_upload.contact_score,
                    'experience': cv_upload.experience_score,
                    'education': cv_upload.education_score,
                    'skills': cv_upload.skills_score,
                    'format': cv_upload.format_score,
                },
                'suggestions': cv_upload.suggestions,
                'processed_at': cv_upload.uploaded_at
            })

        except Exception as e:
            file_data.update({
                'error': str(e),
                'status': 'failed'
            })
            # Clean up if file was saved but processing failed
            if 'cv_upload' in locals() and cv_upload.pk:
                cv_upload.file.delete(save=False)
                cv_upload.delete()

        results.append(file_data)

    return Response({
        'count': len(results),
        'success_count': len([r for r in results if r['status'] == 'success']),
        'results': results
    })

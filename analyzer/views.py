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
import os
from django.core.paginator import Paginator
# Fix your import path as per your folder structure:
from utiliy.suggestions import generate_resume_suggestions


from django.contrib.auth.decorators import login_required


@login_required
def upload_cv(request):
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
def cv_rank(request):
    top_cvs = CVUpload.objects.filter(processed=True).order_by('-overall_score')[:5]
    return render(request, "analyzer/cv_rank.html", {"cvs": top_cvs})



def results(request):
    cvs = CVUpload.objects.filter(processed=True).order_by('-uploaded_at')
    
    
    # Pagination (we'll set 10 CVs per page)
    paginator = Paginator(cvs, 10)  # 10 CVs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "analyzer/results.html", {"page_obj": page_obj})
    

@login_required
def cv_detail(request, cv_id):
    cv = get_object_or_404(CVUpload, id=cv_id, processed=True)
    return render(request, "analyzer/cv_detail.html", {"cv": cv})

@login_required
def delete_cv(request, cv_id):
    if request.method == "POST":
        cv = get_object_or_404(CVUpload, id=cv_id)

        # Delete the file from storage
        if cv.file:
            default_storage.delete(cv.file.name)

        cv.delete()
        messages.success(request, "CV deleted successfully.")

    return redirect("results")

@login_required
@csrf_exempt
def api_upload(request):
    """API endpoint for uploading CVs"""
    if request.method == "POST":
        files = request.FILES.getlist("files")
        if not files:
            return JsonResponse({"error": "No files provided"}, status=400)

        results = []
        parser = CVParser()
        scorer = CVScorer()

        for file in files:
            try:
                # Basic validation
                allowed_extensions = [".pdf", ".doc", ".docx", ".txt"]
                file_ext = os.path.splitext(file.name)[1].lower()

                if file_ext not in allowed_extensions:
                    results.append(
                        {"filename": file.name, "error": "Unsupported file format"}
                    )
                    continue

                # Create and process CV
                cv_upload = CVUpload(file=file, filename=file.name)
                cv_upload.save()

                # Parse and score
                parsed_data = parser.parse_cv(cv_upload.file.path, file_ext)
                scoring_results = scorer.score_cv(parsed_data)

                # Update CV with results
                cv_upload.raw_text = parsed_data["raw_text"]
                cv_upload.contact_info = parsed_data["contact_info"]
                cv_upload.experience = parsed_data["experience"]
                cv_upload.education = parsed_data["education"]
                cv_upload.skills = parsed_data["skills"]
                cv_upload.overall_score = scoring_results["overall_score"]
                cv_upload.contact_score = scoring_results["scores"]["contact"]
                cv_upload.experience_score = scoring_results["scores"]["experience"]
                cv_upload.education_score = scoring_results["scores"]["education"]
                cv_upload.skills_score = scoring_results["scores"]["skills"]
                cv_upload.format_score = scoring_results["scores"]["format"]
                cv_upload.suggestions = scoring_results["suggestions"]
                cv_upload.processed = True
                cv_upload.save()

                results.append(
                    {
                        "id": cv_upload.id,
                        "filename": cv_upload.filename,
                        "overall_score": cv_upload.overall_score,
                        "scores": {
                            "contact": cv_upload.contact_score,
                            "experience": cv_upload.experience_score,
                            "education": cv_upload.education_score,
                            "skills": cv_upload.skills_score,
                            "format": cv_upload.format_score,
                        },
                        "suggestions": cv_upload.suggestions,
                    }
                )

            except Exception as e:
                results.append({"filename": file.name, "error": str(e)})

        return JsonResponse({"results": results})

    return JsonResponse({"error": "Invalid request method"}, status=405)

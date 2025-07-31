# Create your views here.
from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import CVUpload
from .forms import CVUploadForm
from .parser import CVParser
from .cv_scorer import CVScorer
import os
import json


# Import your parser and scorer classes
# from .cv_parser import CVParser
# from .cv_scorer import CVScorer


def upload_cv(request):
    if request.method == "POST":
        form = CVUploadForm(request.POST, request.FILES)

        files = request.FILES.getlist("cv_files")  # Get all uploaded files

        try:
            form.validate_multiple_files(files)  # Custom validation
        except forms.ValidationError as ve:
            for error in ve.error_list:
                messages.error(request, error)
            return render(request, "analyzer/upload.html", {"form": form})

        # No need to check form.is_valid() since we don't use form fields for files
        uploaded_cvs = []
        parser = CVParser()
        scorer = CVScorer()

        for file in files:
            file_ext = os.path.splitext(file.name)[1].lower()

            if file.size > 5 * 1024 * 1024:  # Just in case
                messages.error(request, f"File too large (max 5MB): {file.name}")
                continue

            cv_upload = CVUpload(file=file, filename=file.name)
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

                cv_upload.suggestions = scoring_results.get("suggestions", "")
                cv_upload.processed = True
                cv_upload.save()

                uploaded_cvs.append(cv_upload)

            except Exception as e:
                messages.error(request, f"Error processing {file.name}: {str(e)}")
                cv_upload.delete()

        if uploaded_cvs:
            messages.success(
                request, f"Successfully processed {len(uploaded_cvs)} CV(s)."
            )
            return redirect("results")
        else:
            messages.error(request, "No valid files were processed.")

    else:
        form = CVUploadForm()

    return render(request, "analyzer/upload.html", {"form": form})


def results(request):
    cvs = CVUpload.objects.filter(processed=True)
    return render(request, "analyzer/results.html", {"cvs": cvs})


def cv_detail(request, cv_id):
    cv = get_object_or_404(CVUpload, id=cv_id, processed=True)
    return render(request, "analyzer/cv_detail.html", {"cv": cv})


def delete_cv(request, cv_id):
    if request.method == "POST":
        cv = get_object_or_404(CVUpload, id=cv_id)

        # Delete the file from storage
        if cv.file:
            default_storage.delete(cv.file.name)

        cv.delete()
        messages.success(request, "CV deleted successfully.")

    return redirect("results")


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

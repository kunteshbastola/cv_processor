from django.urls import path
from . import views

urlpatterns = [
    # HTML page
    path(' ', views.upload_cv, name='upload'),
    path('upload/', views.upload_cv, name='upload'),

    # API endpoints
    path('api/upload/', views.api_upload, name='api_upload'),
    path('api/results/', views.api_results, name='api_results'),
    path('api/rank/', views.api_cv_rank, name='api_cv_rank'),
    path('api/cv/<int:cv_id>/', views.api_cv_detail, name='api_cv_detail'),
    path('api/cv/<int:cv_id>/delete/', views.api_delete_cv, name='api_delete_cv'),
]

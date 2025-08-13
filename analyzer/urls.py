from django.urls import path,include
from .views import api_upload
from django.contrib.auth.decorators import login_required
from . import views

urlpatterns = [
    path('upload/', views.upload_cv, name='upload'),

    #api endpoints
    path('api/upload/', views.api_upload, name='api_upload'),
    path('api/results/', views.api_results, name='api_results'),
    path('api/rank/', views.api_cv_rank, name='api_cv_rank'),
    path('api/cv/<int:cv_id>/', views.api_cv_detail, name='api_cv_detail'),
    path('api/cv/<int:cv_id>/delete/', views.api_delete_cv, name='api_delete_cv'),

]
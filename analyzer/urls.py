from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload_cv, name='upload_cv'),         # Upload page, root URL
    path('results/', views.results, name='results'),     # List of processed CVs
    path('cv/<int:cv_id>/', views.cv_detail, name='cv_detail'),  # Detail page for a CV
    path('cv/<int:cv_id>/delete/', views.delete_cv, name='delete_cv'),  # Delete CV
]

from django.urls import path,include
from django.contrib.auth.decorators import login_required
from . import views

urlpatterns = [
    path('', views.upload_cv, name='upload_cv'), 
    path('upload_cv/', views.upload_cv, name='upload_cv'),         # Upload page, root URL
    path('results/', views.results, name='results'), 
    path('cv-rank/', views.cv_rank, name='cv_rank'),  # NEW: Top 5 from all users    # List of processed CVs
    path('cv/<int:cv_id>/', views.cv_detail, name='cv_detail'),  # Detail page for a CV
    path('cv/<int:cv_id>/delete/', views.delete_cv, name='delete_cv'),
    path('accounts/', include('django.contrib.auth.urls')),  
]

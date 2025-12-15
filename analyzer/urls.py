from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    
]



    # path('api/upload/', views.upload_cv, name='upload_cv'),
    # path('api/cv/<int:cv_id>/', views.matched_results, name='matched_results'),
    # path('api/matched/', views.api_cv_suggestions, name='api_cv_suggestions'),
    # path('api/suggestions/', views.upload_and_suggest, name='upload_and_suggest'),


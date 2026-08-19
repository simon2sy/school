from django.urls import path
from . import views

app_name = 'academics'

urlpatterns = [
    path('academics/', views.programs, name='programs'),
    path('academics/<slug:slug>/', views.program_detail, name='program_detail'),
    path('exam-routine/', views.exam_routine, name='exam_routine'),
    path('exam-routine/<int:exam_id>/', views.exam_routine, name='exam_routine_detail'),
    path('results/', views.results, name='results'),
]
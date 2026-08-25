from django.urls import path
from . import views

app_name = 'academics'

urlpatterns = [
    path('academics/', views.programs, name='programs'),
    path('academics/<slug:slug>/', views.program_detail, name='program_detail'),
    path('exam-routine/', views.exam_routine, name='exam_routine'),
    path('exam-routine/<int:exam_id>/', views.exam_routine, name='exam_routine_detail'),
    path('exam-routine/add/', views.exam_routine_add, name='exam_routine_add'),
    path('exam-routine/add/<int:exam_id>/', views.exam_routine_add, name='exam_routine_add_for_exam'),
    path('exam-result/add/', views.exam_result_add, name='exam_result_add'),
    path('results/', views.results, name='results'),
]
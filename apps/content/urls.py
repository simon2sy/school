from django.urls import path
from . import views

app_name = 'content'

urlpatterns = [
    # News
    path('news/', views.news_list, name='news_list'),
    path('news/<slug:slug>/', views.news_detail, name='news_detail'),
    path('news/category/<slug:slug>/', views.news_by_category, name='news_by_category'),

    # Notices
    path('notices/', views.notice_list, name='notice_list'),
    path('notices/<slug:slug>/', views.notice_detail, name='notice_detail'),

    # Events
    path('events/', views.event_list, name='event_list'),
    path('events/<slug:slug>/', views.event_detail, name='event_detail'),

    # Gallery
    path('gallery/', views.gallery, name='gallery'),
    path('gallery/<slug:slug>/', views.gallery_album, name='gallery_album'),
]
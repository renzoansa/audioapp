from django.urls import include, path
from . import views

urlpatterns = [
    path('trim/', views.trim_audio, name='trim_audio'),
]

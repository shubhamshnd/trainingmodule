from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_form, name='create_form'),
    path('preview/', views.preview_form, name='preview_form'),
]

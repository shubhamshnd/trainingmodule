
from django.contrib import admin
from django.urls import path , include
from useri import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.login_view, name='login'),  # Set the login view as the default page
    path('home/', views.home, name='home'),
    path('api/user_trainings/', views.user_trainings, name='user_trainings'),
    path('logout/', views.logout_view, name='logout'),
    path('request-training/', views.request_training, name='request_training'),
    path('get_approvals/<int:request_id>/', views.get_approvals, name='get_approvals'),
    path('assign-superior/', views.assign_superior, name='assign_superior'),
    path('superior-check-requests/', views.superior_check_requests, name='superior_check_requests'),
    path('superior-approve-request/', views.superior_approve_request, name='superior_approve_request'),
    path('superior-reject-request/', views.superior_reject_request, name='superior_reject_request'),
    path('assign-higher-superior/', views.assign_higher_superior, name='assign_higher_superior'),
    path('check_requests/', views.checker_check_requests, name='checker_check_requests'),
    path('approve_request/', views.checker_approve_request, name='checker_approve_request'),
    path('reject_request/', views.checker_reject_request, name='checker_reject_request'),
    path('maker-check-requests/', views.maker_check_requests, name='maker_check_requests'),
    path('easter_egg/', views.easter_egg_page, name='easter_egg_page'),
    path('checker-training-detail/<str:training_programme_title>/', views.checker_training_detail, name='checker_training_detail'),
    path('maker-training-detail/<str:training_programme_title>/', views.maker_training_detail, name='maker_training_detail'),
    path('add_to_training/', views.add_to_training, name='add_to_training'),
    path('formbuilder/', include('formbuilder.urls')),
    path('create_training/', views.create_training, name='create_training'),
    path('select2/', include('django_select2.urls')),
    path('modify/<int:pk>/', views.edit_training, name='modify_training'),
    path('send_training_request/<int:pk>/', views.send_training_request, name='send_training_request'),
    path('get-department-details/', views.get_department_details, name='get_department_details'),
    path('get_training_selected_users/<int:pk>/', views.get_training_selected_users, name='get_training_selected_users'),
    path('store_department_counts/', views.store_department_counts, name='store_department_counts'),
    path('get_department_counts/', views.get_department_counts, name='get_department_counts'),
    path('list_and_finalize_trainings/', views.list_and_finalize_trainings, name='list_and_finalize_trainings'),
    path('get_department_participants/<int:training_id>/', views.get_department_participants, name='get_department_participants'),
    path('checker_finalize_trainings/', views.checker_finalize_trainings, name='checker_finalize_trainings'),
    path('get_training_details/<int:training_id>/', views.get_training_details, name='get_training_details'),
    path('get_checker_training_details/<int:training_id>/', views.get_checker_training_details, name='get_checker_training_details'),
    path('mark-attendance/<int:training_id>/', views.mark_attendance, name='mark_attendance'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

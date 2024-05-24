from django.contrib import admin

# Register your models here.
# admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Role , TrainingProgramme ,Status, RequestTraining

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'employee_name', 'employee_id', 'role']
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('email', 'employee_id', 'employee_name', 'gender', 'date_of_birth', 'blood_group', 'marital_status', 'weight', 'height', 'date_of_joining', 'designation', 'department', 'grade', 'work_order_no', 'work_order_expiry_date', 'item_code', 'contractor_name', 'sub_contractor_name', 'under_sub_contractor_name', 'category', 'pf_code', 'uan_no_pf', 'pf_no', 'pan_no', 'lic_policy_no', 'shift_group', 'section', 'identification_mark_1', 'identification_mark_2', 'contact_no', 'emergency_contact_person', 'emergency_contact_no', 'card_active_status', 'date_of_leaving', 'card_validity', 'card_status', 'esi_no', 'address', 'pin_code', 'taluka', 'district', 'state', 'per_address', 'per_pin_code', 'per_taluka', 'per_district', 'per_state', 'poi', 'poino', 'poa', 'poano', 'bank_name', 'branch_name', 'account_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions', 'role')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email', 'employee_id', 'role'),
        }),
    )
    search_fields = ('username', 'email', 'employee_id', 'employee_name')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions',)


class RoleAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    
    
    
class TrainingProgrammeAdmin(admin.ModelAdmin):
    list_display = ['title']
    search_fields = ['title']
    ordering = ['title']


class StatusAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    ordering = ['name']


class RequestTrainingAdmin(admin.ModelAdmin):
    list_display = ['custom_user', 'training_programme', 'other_training', 'status', 'request_date', 'last_updated']
    search_fields = ['custom_user__username', 'training_programme__title', 'other_training']
    ordering = ['request_date']
    list_filter = ['status', 'training_programme']


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(TrainingProgramme, TrainingProgrammeAdmin)
admin.site.register(Status, StatusAdmin)
admin.site.register(RequestTraining, RequestTrainingAdmin)
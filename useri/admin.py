from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, Role, TrainingProgramme, Status, RequestTraining, 
    VenueMaster, HODTrainingAssignment, TrainerMaster, TrainingSession, AttendanceMaster
)

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
    ordering = ['name']


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
    

class VenueMasterAdmin(admin.ModelAdmin):
    list_display = ['name', 'venue_type']
    search_fields = ['name']
    ordering = ['name']


class HODTrainingAssignmentAdmin(admin.ModelAdmin):
    list_display = ['hod_user', 'assigned_user', 'training_programme', 'other_training', 'status', 'assignment_date']
    search_fields = ['hod_user__username', 'assigned_user__username', 'training_programme__title', 'other_training']
    ordering = ['assignment_date']
    list_filter = ['status', 'training_programme']


class TrainerMasterAdmin(admin.ModelAdmin):
    list_display = ['name', 'trainer_type']
    search_fields = ['name', 'trainer_type']
    ordering = ['name']
    list_filter = ['trainer_type']


class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = ['training_programme', 'custom_training_programme', 'venue', 'trainer', 'created_by', 'created_at', 'date', 'from_time', 'to_time']
    search_fields = ['training_programme__title', 'custom_training_programme', 'venue__name', 'trainer__name', 'created_by__username']
    ordering = ['created_at']
    list_filter = ['training_programme', 'venue', 'trainer']


class AttendanceMasterAdmin(admin.ModelAdmin):
    list_display = ['custom_user', 'training_session', 'attendance_date']
    search_fields = ['custom_user__username', 'training_session__training_programme__title']
    ordering = ['attendance_date']
    list_filter = ['training_session__training_programme', 'attendance_date']


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(TrainingProgramme, TrainingProgrammeAdmin)
admin.site.register(Status, StatusAdmin)
admin.site.register(RequestTraining, RequestTrainingAdmin)
admin.site.register(VenueMaster, VenueMasterAdmin)
admin.site.register(HODTrainingAssignment, HODTrainingAssignmentAdmin)
admin.site.register(TrainerMaster, TrainerMasterAdmin)
admin.site.register(TrainingSession, TrainingSessionAdmin)
admin.site.register(AttendanceMaster, AttendanceMasterAdmin)

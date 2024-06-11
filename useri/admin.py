from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .forms import DepartmentAdminForm
from .models import (
    CustomUser, TrainingProgramme, RequestTraining, 
    VenueMaster, TrainerMaster, TrainingSession, AttendanceMaster, Department
)

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'employee_name', 'employee_id', 'can_assign_trainings', 'is_maker', 'is_checker']
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('email', 'employee_id', 'employee_name', 'gender', 'date_of_birth', 'blood_group')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions', 'can_assign_trainings', 'is_maker', 'is_checker')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email', 'employee_id'),
        }),
    )
    search_fields = ('username', 'email', 'employee_id', 'employee_name')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions')


class TrainingProgrammeAdmin(admin.ModelAdmin):
    list_display = ['title', 'validity']
    search_fields = ['title']
    ordering = ['title']
    fields = ['title', 'validity']
    list_filter = ['validity']


class RequestTrainingAdmin(admin.ModelAdmin):
    list_display = ['custom_user', 'training_programme', 'other_training', 'status', 'request_date', 'last_updated']
    search_fields = ['custom_user__username', 'training_programme__title', 'other_training']
    ordering = ['request_date']
    list_filter = ['status', 'training_programme']
    

class VenueMasterAdmin(admin.ModelAdmin):
    list_display = ['name', 'venue_type']
    search_fields = ['name']
    ordering = ['name']


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


class DepartmentAdmin(admin.ModelAdmin):
    form = DepartmentAdminForm
    list_display = ['name', 'parent', 'head']
    search_fields = ['name', 'head__username']
    ordering = ['name']
    list_filter = ['parent', 'head']
    filter_horizontal = ('members', 'associates')

    fieldsets = (
        (None, {
            'fields': ('name', 'parent')
        }),
        ('Head', {
            'fields': ('head', 'head_role')
        }),
        ('Members', {
            'fields': ('members', 'associates')
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['head'].label_from_instance = lambda obj: f"{obj.employee_name} - {obj.username}"
        form.base_fields['members'].label_from_instance = lambda obj: f"{obj.employee_name} - {obj.username}"
        form.base_fields['associates'].label_from_instance = lambda obj: f"{obj.employee_name} - {obj.username}"
        return form

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # Save is_maker and is_checker for each member
        if form.instance:
            for member in form.instance.members.all():
                role_field_name = f'member_{member.pk}_role'
                member_role = form.cleaned_data.get(role_field_name, '')
                member.is_maker = (member_role == 'maker')
                member.is_checker = (member_role == 'checker')
                member.save()


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(TrainingProgramme, TrainingProgrammeAdmin)
admin.site.register(RequestTraining, RequestTrainingAdmin)
admin.site.register(VenueMaster, VenueMasterAdmin)
admin.site.register(TrainerMaster, TrainerMasterAdmin)
admin.site.register(TrainingSession, TrainingSessionAdmin)
admin.site.register(AttendanceMaster, AttendanceMasterAdmin)
admin.site.register(Department, DepartmentAdmin)
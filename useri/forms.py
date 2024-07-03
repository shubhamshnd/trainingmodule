from django import forms
from .models import DepartmentCount, RequestTraining, TrainingProgramme , HODTrainingAssignment , CustomUser , VenueMaster, TrainerMaster , TrainingSession , Department , SuperiorAssignedTraining , TrainingApproval
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.forms import ModelMultipleChoiceField
import logging
from django.db.models import Q , F , Max
from django.utils import timezone
logger = logging.getLogger(__name__)
class RequestTrainingForm(forms.ModelForm):
    class Meta:
        model = RequestTraining
        fields = ['training_programme', 'other_training', 'user_comment']
        widgets = {
            'training_programme': forms.Select(attrs={'class': 'form-select'}),
            'other_training': forms.TextInput(attrs={'class': 'form-control'}),
            'user_comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['training_programme'].queryset = TrainingProgramme.objects.all()
        self.fields['training_programme'].required = False
        self.fields['other_training'].required = False

    def clean(self):
        cleaned_data = super().clean()
        training_programme = cleaned_data.get("training_programme")
        other_training = cleaned_data.get("other_training")

        if not training_programme and not other_training:
            logger.error("Validation Error: You must select a training programme or specify another training.")
            raise forms.ValidationError("You must select a training programme or specify another training.")
        
        logger.info(f"Form cleaned data: {cleaned_data}")
        return cleaned_data
    
    
    
class TrainingRequestApprovalForm(forms.Form):
    request_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    assignment_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    status_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)  # Updated to required=False
    hod_comment = forms.CharField(widget=forms.Textarea, label='Comment', required=False)
    action = forms.ChoiceField(choices=[('approve', 'Approve'), ('reject', 'Reject')], widget=forms.HiddenInput())

    def clean(self):
        cleaned_data = super().clean()
        request_id = cleaned_data.get('request_id')
        assignment_id = cleaned_data.get('assignment_id')
        status_id = cleaned_data.get('status_id')
        hod_comment = cleaned_data.get('hod_comment')
        action = cleaned_data.get('action')

        if not request_id and not assignment_id:
            raise forms.ValidationError("Request ID or Assignment ID is required.")
        if request_id and not status_id:
            raise forms.ValidationError("Status ID is required for request approvals.")
        if not hod_comment:
            raise forms.ValidationError("Comment is required.")
        if not action:
            raise forms.ValidationError("Action is required.")

        return cleaned_data
    
    
class SuperiorAssignmentForm(forms.ModelForm):
    assigned_users = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )

    class Meta:
        model = SuperiorAssignedTraining
        fields = ['assigned_users', 'training_programme', 'other_training', 'hod_comment']
        widgets = {
            'training_programme': forms.Select(attrs={'class': 'form-select'}),
            'other_training': forms.TextInput(attrs={'class': 'form-control'}),
            'hod_comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        superior_user = kwargs.pop('superior_user', None)
        super().__init__(*args, **kwargs)
        if superior_user:
            self.superior_user = superior_user
            self.fields['assigned_users'].queryset = CustomUser.objects.filter(
                user_departments__in=self.get_all_headed_departments(superior_user)
            ).distinct()
            self.fields['assigned_users'].label_from_instance = self.label_from_instance
        self.fields['training_programme'].queryset = TrainingProgramme.objects.all()
        self.fields['training_programme'].required = False
        self.fields['other_training'].required = False

    def label_from_instance(self, obj):
        return f"{obj.username} - {obj.employee_name}"

    def clean(self):
        cleaned_data = super().clean()
        training_programme = cleaned_data.get("training_programme")
        other_training = cleaned_data.get("other_training")

        if not training_programme and not other_training:
            raise forms.ValidationError("You must select a training programme or specify another training.")
        return cleaned_data

    def get_all_headed_departments(self, superior_user):
        def get_sub_departments(department):
            all_departments = [department]
            sub_departments = department.sub_departments.all()
            for sub_dept in sub_departments:
                all_departments.extend(get_sub_departments(sub_dept))
            return all_departments
        
        all_departments = []
        for department in superior_user.headed_departments.all():
            all_departments.extend(get_sub_departments(department))
        
        return all_departments

    def get_hierarchical_departments(self):
        def get_sub_departments(department):
            hierarchy = [{'department': department, 'members': department.members.all()}]
            sub_departments = department.sub_departments.all()
            for sub_dept in sub_departments:
                hierarchy.extend(get_sub_departments(sub_dept))
            return hierarchy
        
        hierarchical_departments = []
        for department in self.superior_user.headed_departments.all():
            hierarchical_departments.extend(get_sub_departments(department))
        
        return hierarchical_departments
    
    
    
class CheckerApprovalForm(forms.Form):
    request_id = forms.IntegerField(widget=forms.HiddenInput())
    status_id = forms.IntegerField(widget=forms.HiddenInput())
    checker_comment = forms.CharField(widget=forms.Textarea, label='Checker Comment', required=True)

    def clean(self):
        cleaned_data = super().clean()
        request_id = cleaned_data.get('request_id')
        status_id = cleaned_data.get('status_id')
        checker_comment = cleaned_data.get('checker_comment')

        if not request_id:
            raise forms.ValidationError("Request ID is required.")
        if not status_id:
            raise forms.ValidationError("Status ID is required.")
        if not checker_comment:
            raise forms.ValidationError("Checker Comment is required.")

        return cleaned_data


class TrainingCreationForm(forms.ModelForm):
    trainer_type = forms.ChoiceField(
        choices=(('Internal', 'Internal'), ('External', 'External')),
        required=True,
        label='Trainer Type',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    internal_trainer = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(),
        required=False,
        label='Internal Trainer',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    custom_training_programme = forms.CharField(
        required=False,
        label='Other Training Programme',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    venue_type = forms.ChoiceField(
        choices=VenueMaster.VENUE_TYPE_CHOICES,
        required=True,
        label='Venue Type',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    online_training_link = forms.URLField(
        required=False,
        label='Online Training Link',
        widget=forms.URLInput(attrs={'class': 'form-control'})
    )
    online_training_file = forms.FileField(
        required=False,
        label='Online Training File',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    needs_hod_nomination = forms.BooleanField(required=False, label='Needs HOD Nomination')

    class Meta:
        model = TrainingSession
        fields = [
            'training_programme', 'custom_training_programme', 'venue_type', 
            'venue', 'trainer_type', 'internal_trainer', 'date', 
            'from_time', 'to_time', 'online_training_link', 'online_training_file', 
            'needs_hod_nomination'
        ]
        labels = {
            'training_programme': 'Training Programme',
            'venue_type': 'Venue Type',
            'venue': 'Venue',
            'date': 'Date',
            'from_time': 'From Time',
            'to_time': 'To Time',
            'online_training_link': 'Online Training Link',
            'online_training_file': 'Online Training File',
            'needs_hod_nomination': 'Needs HOD Nomination'
        }
        widgets = {
            'training_programme': forms.Select(attrs={'class': 'form-select'}),
            'venue': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'from_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'to_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super(TrainingCreationForm, self).__init__(*args, **kwargs)
        self.fields['internal_trainer'].queryset = CustomUser.objects.filter(
            work_order_no=''
        ).order_by('employee_name')
        self.fields['internal_trainer'].label_from_instance = self.label_from_instance

        # Set an initial empty queryset for venues
        self.fields['venue'].queryset = VenueMaster.objects.none()

        # Populate the venue queryset based on the selected venue_type
        if 'venue_type' in self.data:
            try:
                venue_type = self.data.get('venue_type')
                self.fields['venue'].queryset = VenueMaster.objects.filter(venue_type=venue_type).order_by('name')
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty queryset
        elif self.instance.pk:
            self.fields['venue'].queryset = self.instance.venue.__class__.objects.all().order_by('name')

    @staticmethod
    def label_from_instance(obj):
        return f"{obj.employee_name} - {obj.username}"

    def clean(self):
        cleaned_data = super().clean()
        venue_type = cleaned_data.get("venue_type")
        online_training_link = cleaned_data.get("online_training_link")
        online_training_file = cleaned_data.get("online_training_file")

        if venue_type == 'Online':
            if not online_training_link and not online_training_file:
                raise forms.ValidationError("For online training, either a link or a file is required.")
            self.fields['internal_trainer'].required = False
            self.fields['trainer_type'].required = False
        return cleaned_data

class ExternalTrainerForm(forms.ModelForm):
    existing_trainer = forms.ModelChoiceField(
        queryset=TrainerMaster.objects.filter(trainer_type='External'),
        required=False,
        label='Select Existing Trainer',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = TrainerMaster
        fields = ['existing_trainer', 'name', 'email', 'phone_number', 'city']
        labels = {
            'name': 'Name',
            'email': 'Email',
            'phone_number': 'Phone Number',
            'city': 'City'
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        super(ExternalTrainerForm, self).__init__(*args, **kwargs)
        self.fields['existing_trainer'].label_from_instance = lambda obj: f"{obj.name} ({obj.email})"
        self.fields['existing_trainer'].required = False  # Ensure this field is not required
        self.fields['email'].required = False
        self.fields['phone_number'].required = False
        self.fields['city'].required = False

class TrainingRequestForm(forms.ModelForm):
    needs_hod_nomination = forms.BooleanField(required=False, initial=False)

    class Meta:
        model = TrainingSession
        fields = ['date', 'from_time', 'to_time', 'deadline_to_complete', 'needs_hod_nomination']
        labels = {
            'date': 'Date',
            'from_time': 'From Time',
            'to_time': 'To Time',
            'deadline_to_complete': 'Deadline to Complete'
        }
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'from_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'to_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'deadline_to_complete': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
        }

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get("date")
        from_time = cleaned_data.get("from_time")
        to_time = cleaned_data.get("to_time")
        deadline_to_complete = cleaned_data.get("deadline_to_complete")
        venue_type = self.instance.venue.venue_type if self.instance.venue else None

        if date is None:
            self.add_error('date', 'Date is required.')
        if from_time is None:
            self.add_error('from_time', 'From time is required.')
        if to_time is None:
            self.add_error('to_time', 'To time is required.')
        if venue_type == 'Online' and deadline_to_complete is None:
            self.add_error('deadline_to_complete', 'Deadline to complete is required for online training.')

        return cleaned_data

class DepartmentCountForm(forms.Form):
    department_id = forms.IntegerField(widget=forms.HiddenInput())
    department_name = forms.CharField(required=False, widget=forms.HiddenInput())
    head_name = forms.CharField(required=False, widget=forms.HiddenInput())
    available_employees = forms.IntegerField(required=False, widget=forms.HiddenInput())
    available_associates = forms.IntegerField(required=False, widget=forms.HiddenInput())
    required_employees = forms.IntegerField(min_value=0, required=False)
    required_associates = forms.IntegerField(min_value=0, required=False)

    def clean_required_employees(self):
        required_employees = self.cleaned_data.get('required_employees') or 0
        available_employees = self.cleaned_data.get('available_employees') or 0
        if required_employees > available_employees:
            raise forms.ValidationError("Required employees cannot be more than available employees.")
        return required_employees

    def clean_required_associates(self):
        required_associates = self.cleaned_data.get('required_associates') or 0
        available_associates = self.cleaned_data.get('available_associates') or 0
        if required_associates > available_associates:
            raise forms.ValidationError("Required associates cannot be more than available associates.")
        return required_associates

    def clean(self):
        cleaned_data = super().clean()
        department_id = cleaned_data.get("department_id")
        if not department_id:
            raise forms.ValidationError("Department ID is required.")
        return cleaned_data
        
class TrainingApprovalForm(forms.ModelForm):
    class Meta:
        model = TrainingApproval
        fields = ['training_session', 'department', 'head', 'selected_participants', 'removed_participants', 'removal_reasons', 'approved', 'approval_timestamp', 'pending_approval']

class ReasonForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea, required=True)
    
    

class ParticipantsForm(forms.Form):
    nominated_members = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        required=False
    )
    nominated_associates = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        required=False
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        training = kwargs.pop('training', None)
        super().__init__(*args, **kwargs)

        logger.info(f"Initializing ParticipantsForm - User: {user}, Training: {training}")

        if user and training:
            departments = Department.objects.filter(head=user)
            
            nominated_employees_qs = CustomUser.objects.filter(
                user_departments__in=departments
            ).distinct()

            nominated_associates_qs = CustomUser.objects.filter(
                associated_departments__in=departments
            ).distinct()

            self.fields['nominated_members'].queryset = nominated_employees_qs
            self.fields['nominated_associates'].queryset = nominated_associates_qs

            logger.info(f"Form initialization - User: {user.username}, Training: {training.id}")
            logger.info(f"Nominated Members Queryset IDs: {list(nominated_employees_qs.values_list('id', flat=True))}")
            logger.info(f"Nominated Associates Queryset IDs: {list(nominated_associates_qs.values_list('id', flat=True))}")

    def clean(self):
        cleaned_data = super().clean()
        logger.info(f"Form cleaning - Cleaned data: {cleaned_data}")
        return cleaned_data
            
            
            
      
class DepartmentAdminForm(forms.ModelForm):
    HEAD_ROLE_CHOICES = [
        ('', 'None'),
        ('maker', 'Head is Maker'),
        ('checker', 'Head is Checker'),
    ]

    head_role = forms.ChoiceField(
        choices=HEAD_ROLE_CHOICES,
        widget=forms.RadioSelect,
        label="Head Role",
        required=False
    )

    class Meta:
        model = Department
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['head'].queryset = CustomUser.objects.all().order_by('employee_name')
        self.fields['members'].queryset = CustomUser.objects.filter(work_order_no='').order_by('employee_name')
        self.fields['associates'].queryset = CustomUser.objects.exclude(work_order_no='').order_by('employee_name')

        # Initialize head_role based on the current head's is_maker and is_checker values
        if self.instance and self.instance.head:
            if self.instance.head.is_maker:
                self.fields['head_role'].initial = 'maker'
            elif self.instance.head.is_checker:
                self.fields['head_role'].initial = 'checker'
            else:
                self.fields['head_role'].initial = ''

        # Dynamically add member role fields
        if self.instance and self.instance.pk:
            for member in self.instance.members.all():
                role_field_name = f'member_{member.pk}_role'
                self.fields[role_field_name] = forms.ChoiceField(
                    choices=self.HEAD_ROLE_CHOICES,
                    widget=forms.RadioSelect,
                    label=f"Role for {member.employee_name}",
                    required=False
                )
                if member.is_maker:
                    self.fields[role_field_name].initial = 'maker'
                elif member.is_checker:
                    self.fields[role_field_name].initial = 'checker'
                else:
                    self.fields[role_field_name].initial = ''

        # Add counts to the form instance for the template
        self.associate_count = self.instance.associates.count() if self.instance.pk else 0
        self.member_count = self.instance.members.count() if self.instance.pk else 0

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Save instance first to get an ID for many-to-many operations
        if commit:
            instance.save()

        # Save head_role
        if instance.head:
            head_role = self.cleaned_data['head_role']
            instance.head.is_maker = (head_role == 'maker')
            instance.head.is_checker = (head_role == 'checker')
            instance.head.save()

        if commit:
            self.save_m2m()

        # Save roles for each member
        if instance.pk:
            for member in instance.members.all():
                role_field_name = f'member_{member.pk}_role'
                member_role = self.cleaned_data.get(role_field_name, '')
                member.is_maker = (member_role == 'maker')
                member.is_checker = (member_role == 'checker')
                member.save()

        return instance
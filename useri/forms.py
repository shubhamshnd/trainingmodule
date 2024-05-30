from django import forms
from .models import RequestTraining, TrainingProgramme , HODTrainingAssignment , CustomUser , VenueMaster, TrainerMaster , TrainingSession

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
            raise forms.ValidationError("You must select a training programme or specify another training.")
        return cleaned_data


class TrainingRequestApprovalForm(forms.Form):
    request_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    assignment_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    status_id = forms.IntegerField(widget=forms.HiddenInput())
    hod_comment = forms.CharField(widget=forms.Textarea, label='HOD Comment', required=False)
    checker_comment = forms.CharField(widget=forms.Textarea, label='Checker Comment', required=False)

    def clean(self):
        cleaned_data = super().clean()
        request_id = cleaned_data.get('request_id')
        assignment_id = cleaned_data.get('assignment_id')
        status_id = cleaned_data.get('status_id')
        hod_comment = cleaned_data.get('hod_comment')
        checker_comment = cleaned_data.get('checker_comment')

        if not request_id and not assignment_id:
            raise forms.ValidationError("Request ID or Assignment ID is required.")
        if not status_id:
            raise forms.ValidationError("Status ID is required.")
        if not hod_comment and not checker_comment:
            raise forms.ValidationError("HOD or Checker comment is required.")

        return cleaned_data


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


class HODTrainingAssignmentForm(forms.ModelForm):
    assigned_users = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )

    class Meta:
        model = HODTrainingAssignment
        fields = ['assigned_users', 'training_programme', 'other_training', 'hod_comment']
        widgets = {
            'training_programme': forms.Select(attrs={'class': 'form-select'}),
            'other_training': forms.TextInput(attrs={'class': 'form-control'}),
            'hod_comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        hod_user = kwargs.pop('hod_user', None)
        super().__init__(*args, **kwargs)
        if hod_user:
            self.fields['assigned_users'].queryset = CustomUser.objects.filter(department=hod_user.department)
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

    class Meta:
        model = TrainingSession
        fields = ['training_programme', 'custom_training_programme', 'venue_type', 'venue', 'trainer_type', 'internal_trainer', 'date', 'from_time', 'to_time', 'online_training_link', 'online_training_file']
        labels = {
            'training_programme': 'Training Programme',
            'venue_type': 'Venue Type',
            'venue': 'Venue',
            'date': 'Date',
            'from_time': 'From Time',
            'to_time': 'To Time',
            'online_training_link': 'Online Training Link',
            'online_training_file': 'Online Training File'
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
            card_validity__year__gt=2045
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



class TrainingRequestForm(forms.ModelForm):
    class Meta:
        model = TrainingSession
        fields = ['date', 'from_time', 'to_time']
        labels = {
            'date': 'Date',
            'from_time': 'From Time',
            'to_time': 'To Time'
        }
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'from_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'to_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'})
        }
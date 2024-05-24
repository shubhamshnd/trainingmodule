from django import forms
from .models import RequestTraining, TrainingProgramme , HODTrainingAssignment , CustomUser

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
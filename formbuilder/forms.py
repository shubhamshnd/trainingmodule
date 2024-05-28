from django import forms
from .models import Form, Question, Choice

class FormForm(forms.ModelForm):
    class Meta:
        model = Form
        fields = ['title', 'description']

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'question_type']

class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['text']

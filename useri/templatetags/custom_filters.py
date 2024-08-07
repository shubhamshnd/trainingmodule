from django import template
from useri.models import RequestTraining, SuperiorAssignedTraining
register = template.Library()
from django.utils.html import format_html
@register.filter
def is_instance(value, class_name):
    return value.__class__.__name__ == class_name

@register.filter(name='add_class')
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})


@register.filter(name='is_approved_by')
def is_approved_by(request, user):
    if isinstance(request, RequestTraining):
        return request.approvals.filter(approver=user).exists()
    elif isinstance(request, SuperiorAssignedTraining):
        return request.assigned_by == user  # or any other condition to check approval for SuperiorAssignedTraining
    return False


@register.filter
def get_field(form, field_name):
    return form[field_name]


@register.filter
def get_class_name(value):
    return value.__class__.__name__
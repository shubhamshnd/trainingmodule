from django import template

register = template.Library()

@register.filter
def is_instance(value, class_name):
    return value.__class__.__name__ == class_name

@register.filter(name='add_class')
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})

from django import template

register = template.Library()

@register.filter
def is_instance(value, class_name):
    return value.__class__.__name__ == class_name

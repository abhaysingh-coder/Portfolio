from django import template

register = template.Library()

@register.filter
def clean_name(value):
    return value.replace('-', ' ').replace('_', ' ')
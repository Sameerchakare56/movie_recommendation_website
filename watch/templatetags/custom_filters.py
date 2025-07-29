from django import template

register = template.Library()
 
@register.filter
def get_item(dictionary, key):
    return dictionary.get(key) 

@register.filter
def endswith(value, arg):
    """Returns True if value ends with arg (case-insensitive)."""
    return str(value).lower().endswith(str(arg).lower()) 
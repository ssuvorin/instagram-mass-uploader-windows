from django import template
import json

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary by key
    Usage: {{ my_dict|get_item:key_variable }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def pprint(value):
    """
    Pretty print a JSON object
    Usage: {{ my_json|pprint }}
    """
    try:
        if isinstance(value, str):
            return json.dumps(json.loads(value), indent=2)
        else:
            return json.dumps(value, indent=2)
    except:
        return str(value) 
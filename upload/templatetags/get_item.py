from django.template.defaulttags import register

@register.filter
def get_item(arr, i):
    try:
        return arr[i]
    except IndexError:
        return 'Null'


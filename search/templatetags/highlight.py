# Standard lib imports
import re

# Django imports
from django import template
from django.utils.html import format_html
from django.utils.encoding import smart_unicode

register = template.Library()

def highlight(value, arg):
    """Wraps search term in highlight span securely to avoid XSS attack"""
    try:
        arg = arg.replace(r'&quot;', '')
        exp = re.compile('(.+)?(' + re.escape(arg) + ')(.+)?', re.IGNORECASE)
        if exp.search(value):
            g = exp.search(value)
            before = g.group(1) or ''
            match = g.group(2)
            after = g.group(3) or ''
            # Have to use smart_text() to ensure that unicode is encoded
            # properly
            html = format_html('{}<span class="highlight">{}</span>{}', 
                               before,
                               match,
                               after)
            # value = exp.sub(html, value)
            value = html
    # NULL throws Attribute Error, if it's an int it throws typeerror,
    # so we have to handle both
    except (AttributeError, TypeError):
        pass

    return smart_unicode(value)

register.filter('highlight', highlight)


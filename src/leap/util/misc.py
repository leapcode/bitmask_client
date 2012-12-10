"""
misc utils
"""


class ImproperlyConfigured(Exception):
    """
    """


def null_check(value, value_name):
    try:
        assert value is not None
    except AssertionError:
        raise ImproperlyConfigured(
            "%s parameter cannot be None" % value_name)

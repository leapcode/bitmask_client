from .config import APP_BASE_NAME, APP_PREFIX, BRANDED_BUILD, BRANDED_OPTS


def get_name():
    if BRANDED_BUILD is True:
        return APP_PREFIX + BRANDED_OPTS.get('short_name', 'name_unknown')
    else:
        return APP_BASE_NAME


def get_shortname():
    if BRANDED_BUILD is True:
        return BRANDED_OPTS.get('short_name', 'name_unknown')

__all__ = ['get_name']

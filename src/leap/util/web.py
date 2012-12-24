"""
web related utilities
"""


class UsageError(Exception):
    """ """


def get_https_domain_and_port(full_domain):
    """
    returns a tuple with domain and port
    from a full_domain string that can
    contain a colon
    """
    full_domain = unicode(full_domain)
    if full_domain is None:
        return None, None

    https_sch = "https://"
    http_sch = "http://"

    if full_domain.startswith(https_sch):
        full_domain = full_domain.lstrip(https_sch)
    elif full_domain.startswith(http_sch):
        raise UsageError(
            "cannot be called with a domain "
            "that begins with 'http://'")

    domain_split = full_domain.split(':')
    _len = len(domain_split)
    if _len == 1:
        domain, port = full_domain, 443
    elif _len == 2:
        domain, port = domain_split
    else:
        raise UsageError(
            "must be called with one only parameter"
            "in the form domain[:port]")
    return domain, port

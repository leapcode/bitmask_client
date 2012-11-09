"""
web related utilities
"""


def get_https_domain_and_port(full_domain):
    """
    returns a tuple with domain and port
    from a full_domain string that can
    contain a colon
    """
    domain_split = full_domain.split(':')
    _len = len(domain_split)
    if _len == 1:
        domain, port = full_domain, 443
    if _len == 2:
        domain, port = domain_split
    return domain, port

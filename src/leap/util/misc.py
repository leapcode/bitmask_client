"""
misc utils
"""
import psutil

from leap.base.constants import OPENVPN_BIN


class ImproperlyConfigured(Exception):
    """
    """


def null_check(value, value_name):
    try:
        assert value is not None
    except AssertionError:
        raise ImproperlyConfigured(
            "%s parameter cannot be None" % value_name)


def get_openvpn_pids():
    # binary name might change

    openvpn_pids = []
    for p in psutil.process_iter():
        try:
            # XXX Not exact!
            # Will give false positives.
            # we should check that cmdline BEGINS
            # with openvpn or with our wrapper
            # (pkexec / osascript / whatever)
            if OPENVPN_BIN in ' '.join(p.cmdline):
                openvpn_pids.append(p.pid)
        except psutil.error.AccessDenied:
            pass
    return openvpn_pids

import os

from leap.util.fileutil import which


def is_pkexec_in_system():
    pkexec_path = which('pkexec')
    if not pkexec_path:
        return False
    return os.access(pkexec_path, os.X_OK)

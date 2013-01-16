"""
DEBUG! ----------- gnutls lib: libgnutls.26.dylib
DEBUG! ----------- gnutls lib: /usr/local/lib/libgnutls.26.dylib
DEBUG! ----------- gnutls lib: /opt/local/lib/libgnutls.26.dylib
DEBUG! ----------- gnutls lib: libgnutls-extra.26.dylib
DEBUG! ----------- gnutls lib: /usr/local/lib/libgnutls-extra.26.dylib
DEBUG! ----------- gnutls lib: /opt/local/lib/libgnutls-extra.26.dylib
"""
import sys

# hackaround pyinstaller ctypes dependencies discovery 
# See:
# http://www.pyinstaller.org/wiki/Features/CtypesDependencySupport#SolutioninPyInstaller
# gnutls.library.load_library is using a style of dep loading
# unsupported by pyinstaller. So we force these imports here.

if sys.platform == "darwin":
    from ctypes import CDLL
    try:
        CDLL("libgnutls.26.dylib")
    except OSError:
        pass
    try:
        CDLL("libgnutls-extra.26.dylib")
    except OSError:
        pass

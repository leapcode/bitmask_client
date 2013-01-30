try:
    import sip
    sip.setapi('QString', 2)
    sip.setapi('QVariant', 2)
except ValueError:
    pass

import intro
import connect
import last
import login
import mixins
import providerinfo
import providerselect
import providersetup
import register

__all__ = [
    'intro',
    'connect',
    'last',
    'login',
    'mixins',
    'providerinfo',
    'providerselect',
    'providersetup',
    'register',
    ]  # ,'wizard']

try:
    import sip
    sip.setapi('QString', 2)
    sip.setapi('QVariant', 2)
except ValueError:
    pass

import intro
import last
import login
import mixins
import providerinfo
import providerselect
import providersetup
import register
import regvalidation

__all__ = [
    'intro',
    'last',
    'login',
    'mixins',
    'providerinfo',
    'providerselect',
    'providersetup',
    'register',
    'regvalidation']  # ,'wizard']

try:
    import sip
    sip.setapi('QString', 2)
    sip.setapi('QVariant', 2)
except ValueError:
    pass

import firstrun
import firstrun.wizard

__all__ = ['firstrun', 'firstrun.wizard']

try:
    import sip
    sip.setapi('QString', 2)
    sip.setapi('QVariant', 2)
except ValueError:
    pass

import firstrun

__all__ = ['firstrun']

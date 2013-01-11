import os
import logging

logger = logging.getLogger(__name__)


def get_mac_cabundle():
    # hackaround bundle error
    # XXX this needs a better fix!
    f = os.path.split(__file__)[0]
    sep = os.path.sep
    f_ = sep.join(f.split(sep)[:-2])
    verify = os.path.join(f_, 'cacert.pem')
    #logger.error('VERIFY PATH = %s' % verify)
    exists = os.path.isfile(verify)
    #logger.error('do exist? %s', exists)
    return verify

import os
import stat
import logging

logger = logging.getLogger(__name__)


def check_and_fix_urw_only(cert):
    """
    Test for 600 mode and try to set it if anything different found

    Might raise OSError

    @param cert: Certificate path
    @type cert: str
    """
    mode = stat.S_IMODE(os.stat(cert).st_mode)

    if mode != int('600', 8):
        try:
            logger.warning('Bad permission on %s attempting to set 600' %
                           (cert,))
            os.chmod(cert, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            logger.error('Error while trying to chmod 600 %s' %
                         cert)
            raise

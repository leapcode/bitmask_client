import os
import stat
import logging
import time

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


def get_mtime(filename):
    """
    Returns the modified time or None if the file doesn't exist

    @param filename: path to check
    @type filename: str

    @rtype: str
    """
    try:
        _mtime = os.stat(filename)[8]
        mtime = time.strftime("%c GMT", time.gmtime(_mtime))
        return mtime
    except OSError:
        return None

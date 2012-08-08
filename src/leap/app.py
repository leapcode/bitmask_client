import logging
# This is only needed for Python v2 but is harmless for Python v3.
import sip
sip.setapi('QVariant', 2)
from PyQt4.QtGui import (QApplication, QSystemTrayIcon, QMessageBox)

from leap.baseapp.mainwindow import LeapWindow

logging.basicConfig()
logger = logging.getLogger(name=__name__)


def main():
    """
    launches the main event loop
    long live to the (hidden) leap window!
    """
    import sys
    from leap.util import leap_argparse
    parser, opts = leap_argparse.init_leapc_args()
    debug = getattr(opts, 'debug', False)

    #XXX get debug level and set logger accordingly
    if debug:
        logger.setLevel('DEBUG')
        logger.debug('args: %s' % opts)

    app = QApplication(sys.argv)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Systray",
                             "I couldn't detect any \
system tray on this system.")
        sys.exit(1)
    if not debug:
        QApplication.setQuitOnLastWindowClosed(False)

    window = LeapWindow(opts)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

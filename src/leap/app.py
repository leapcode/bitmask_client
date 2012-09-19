# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import logging
# This is only needed for Python v2 but is harmless for Python v3.
import sip
sip.setapi('QVariant', 2)
from PyQt4.QtGui import (QApplication, QSystemTrayIcon, QMessageBox)

from leap import __version__ as VERSION
from leap.baseapp.mainwindow import LeapWindow


def main():
    """
    launches the main event loop
    long live to the (hidden) leap window!
    """
    import sys
    from leap.util import leap_argparse
    parser, opts = leap_argparse.init_leapc_args()
    debug = getattr(opts, 'debug', False)

    # XXX get severity from command line args
    if debug:
        level = logging.DEBUG
    else:
        level = logging.WARNING

    logger = logging.getLogger(name='leap')
    logger.setLevel(level)
    console = logging.StreamHandler()
    console.setLevel(level)
    formatter = logging.Formatter(
        '%(asctime)s '
        '- %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)

    logger.info('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    logger.info('LEAP client version %s', VERSION)
    logger.info('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    logfile = getattr(opts, 'log_file', False)
    if logfile:
        logger.debug('setting logfile to %s ', logfile)
        fileh = logging.FileHandler(logfile)
        fileh.setLevel(logging.DEBUG)
        fileh.setFormatter(formatter)
        logger.addHandler(fileh)

    logger.info('Starting app')
    app = QApplication(sys.argv)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Systray",
                             "I couldn't detect"
                             "any system tray on this system.")
        sys.exit(1)
    if not debug:
        QApplication.setQuitOnLastWindowClosed(False)

    window = LeapWindow(opts)
    if debug:
        window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

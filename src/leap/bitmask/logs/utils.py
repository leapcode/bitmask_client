import logging
import sys

from leap.bitmask.config import flags
from leap.bitmask.logs import LOG_FORMAT
from leap.bitmask.logs.log_silencer import SelectiveSilencerFilter
from leap.bitmask.logs.safezmqhandler import SafeZMQHandler
from leap.bitmask.logs.streamtologger import StreamToLogger
from leap.bitmask.platform_init import IS_WIN

import logbook
from logbook.more import ColorizedStderrHandler


def get_logger():
    level = logbook.WARNING
    if flags.DEBUG:
        level = logbook.NOTSET

    # This handler consumes logs not handled by the others
    null_handler = logbook.NullHandler(bubble=False)
    null_handler.push_application()

    silencer = SelectiveSilencerFilter()

    zmq_handler = SafeZMQHandler('tcp://127.0.0.1:5000', multi=True,
                                 level=level, filter=silencer.filter)
    zmq_handler.push_application()

    file_handler = logbook.FileHandler('bitmask.log', format_string=LOG_FORMAT,
                                       bubble=True, filter=silencer.filter)
    file_handler.push_application()

    # don't use simple stream, go for colored log handler instead
    # stream_handler = logbook.StreamHandler(sys.stdout,
    #                                        format_string=LOG_FORMAT,
    #                                        bubble=True)
    # stream_handler.push_application()
    stream_handler = ColorizedStderrHandler(
        level=level, format_string=LOG_FORMAT, bubble=True,
        filter=silencer.filter)
    stream_handler.push_application()

    logger = logbook.Logger('leap')

    return logger


def replace_stdout_stderr_with_logging(logger):
    """
    NOTE:
        we are not using this right now (see commented lines on app.py),
        this needs to be reviewed since the log handler has changed.

    Replace:
        - the standard output
        - the standard error
        - the twisted log output
    with a custom one that writes to the logger.
    """
    # Disabling this on windows since it breaks ALL THE THINGS
    # The issue for this is #4149
    if not IS_WIN:
        sys.stdout = StreamToLogger(logger, logging.DEBUG)
        sys.stderr = StreamToLogger(logger, logging.ERROR)

        # Replace twisted's logger to use our custom output.
        from twisted.python import log
        log.startLogging(sys.stdout)

import logging
import sys

from leap.bitmask.logs import LOG_FORMAT
from leap.bitmask.logs.log_silencer import SelectiveSilencerFilter
from leap.bitmask.logs.leap_log_handler import LeapLogHandler
from leap.bitmask.logs.streamtologger import StreamToLogger
from leap.bitmask.platform_init import IS_WIN


def create_logger(debug=False, logfile=None, replace_stdout=True):
    """
    Create the logger and attach the handlers.

    :param debug: the level of the messages that we should log
    :type debug: bool
    :param logfile: the file name of where we should to save the logs
    :type logfile: str
    :return: the new logger with the attached handlers.
    :rtype: logging.Logger
    """
    # TODO: get severity from command line args
    if debug:
        level = logging.DEBUG
    else:
        level = logging.WARNING

    # Create logger and formatter
    logger = logging.getLogger(name='leap')
    logger.setLevel(level)
    formatter = logging.Formatter(LOG_FORMAT)

    # Console handler
    try:
        import coloredlogs
        console = coloredlogs.ColoredStreamHandler(level=level)
    except ImportError:
        console = logging.StreamHandler()
        console.setLevel(level)
        console.setFormatter(formatter)
        using_coloredlog = False
    else:
        using_coloredlog = True

    if using_coloredlog:
        replace_stdout = False

    silencer = SelectiveSilencerFilter()
    console.addFilter(silencer)
    logger.addHandler(console)
    logger.debug('Console handler plugged!')

    # LEAP custom handler
    leap_handler = LeapLogHandler()
    leap_handler.setLevel(level)
    leap_handler.addFilter(silencer)
    logger.addHandler(leap_handler)
    logger.debug('Leap handler plugged!')

    # File handler
    if logfile is not None:
        logger.debug('Setting logfile to %s ', logfile)
        fileh = logging.FileHandler(logfile)
        fileh.setLevel(logging.DEBUG)
        fileh.setFormatter(formatter)
        fileh.addFilter(silencer)
        logger.addHandler(fileh)
        logger.debug('File handler plugged!')

    if replace_stdout:
        replace_stdout_stderr_with_logging(logger)

    return logger


def replace_stdout_stderr_with_logging(logger):
    """
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

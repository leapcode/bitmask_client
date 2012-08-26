import logging
logger = logging.getLogger(name=__name__)


class EIPChecker(object):
    """
    Executes all tests needed
    to ensure a EIPConnection
    can be sucessful
    """
    def __init__(self):
        pass

    def do_all_checks(self, checker=None):
        """
        just runs all tests in a row.
        will raise if some error encounter.
        catching those exceptions is not
        our responsibility at this moment
        """
        if not checker:
            checker = self

        # let's call all tests
        # needed for a sane eip session.

        checker.dump_default_eipconfig()
        checker.check_is_there_default_provider()
        checker.fetch_definition()
        checker.fetch_eip_config()
        checker.check_complete_eip_config()
        checker.ping_gateway()

    def dump_default_eipconfig(self):
        raise NotImplementedError

    def check_is_there_default_provider(self):
        raise NotImplementedError

    def fetch_definition(self):
        raise NotImplementedError

    def fetch_eip_config(self):
        raise NotImplementedError

    def check_complete_eip_config(self):
        raise NotImplementedError

    def ping_gateway(self):
        raise NotImplementedError

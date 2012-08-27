import logging
logger = logging.getLogger(name=__name__)
import os

from leap.base import config as baseconfig
from leap.eip import config as eipconfig
from leap.eip import constants as eipconstants


class EIPChecker(object):
    """
    Several tests needed
    to ensure a EIPConnection
    can be sucessful
    """
    #def __init__(self):
        ## no init needed atm..
        #pass

    def run_all(self, checker=None):
        """
        runs all checks in a row.
        will raise if some error encountered.
        catching those exceptions is not
        our responsibility at this moment
        """
        if not checker:
            checker = self

        # let's call all tests
        # needed for a sane eip session.

        checker.check_default_eipconfig()
        checker.check_is_there_default_provider()
        checker.fetch_definition()
        checker.fetch_eip_config()
        checker.check_complete_eip_config()
        checker.ping_gateway()

    # public checks

    def check_default_eipconfig(self):
        """
        checks if default eipconfig exists,
        and dumps a default file if not
        """
        # it *really* does not make sense to
        # dump it right now, we can get an in-memory
        # config object and dump it to disk in a
        # later moment
        if not self._is_there_default_eipconfig():
            self._dump_default_eipconfig()

    def check_is_there_default_provider(self):
        raise NotImplementedError

    def fetch_definition(self):
        # check_and_get_definition_file
        raise NotImplementedError

    def fetch_eip_config(self):
        raise NotImplementedError

    def check_complete_eip_config(self):
        raise NotImplementedError

    def ping_gateway(self):
        raise NotImplementedError

    # private helpers

    def _get_default_eipconfig_path(self):
        return baseconfig.get_config_file(eipconstants.EIP_CONFIG)

    def _is_there_default_eipconfig(self):
        return os.path.isfile(
            self._get_default_eipconfig_path())

    def _dump_default_eipconfig(self):
        eipconfig.dump_default_eipconfig(
            self._get_default_eipconfig_path())

import json
import logging
import os

logger = logging.getLogger(name=__name__)

import requests

from leap.base import config as baseconfig
from leap.base import constants as baseconstants
from leap.eip import config as eipconfig
from leap.eip import constants as eipconstants
from leap.eip import exceptions as eipexceptions
from leap.util.fileutil import mkdir_p


class EIPChecker(object):
    """
    Several tests needed
    to ensure a EIPConnection
    can be sucessful
    use run_all to run all checks.
    """

    def __init__(self, fetcher=requests):
        """
        we do not want to accept too many
        argument on init. we want tests
        to be explicitely run.
        """
        self.config = None
        self.fetcher = fetcher

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

        # TODO: get rid of check_default.
        # check_complete should
        # be enough.
        checker.check_default_eipconfig()

        checker.check_is_there_default_provider()
        checker.fetch_definition()
        checker.fetch_eip_config()
        checker.check_complete_eip_config()
        #checker.ping_gateway()

    # public checks

    def check_default_eipconfig(self):
        """
        checks if default eipconfig exists,
        and dumps a default file if not
        """
        # XXX ONLY a transient check
        # because some old function still checks
        # for eip config at the beginning.

        # it *really* does not make sense to
        # dump it right now, we can get an in-memory
        # config object and dump it to disk in a
        # later moment
        if not self._is_there_default_eipconfig():
            self._dump_default_eipconfig()

    def check_is_there_default_provider(self, config=None):
        """
        raises EIPMissingDefaultProvider if no
        default provider found on eip config.
        This is catched by ui and runs FirstRunWizard (MVS+)
        """
        # if config is not None:
        # config = config
        # else: self.get_eipconfig
        # XXX parse EIPConfig.
        # XXX get default_provider.
        eipcfg = self._get_default_eipconfig_path()
        with open(eipcfg, 'r') as fp:
            config = json.load(fp)
        provider = config.get('provider', None)
        if provider is None:
            raise eipexceptions.EIPMissingDefaultProvider
        if config:
            self.config = config
        return True

    def fetch_definition(self, skip_download=False,
                         config=None, uri=None):
        # check_and_get_definition_file
        """
        fetches a definition file from server
        """
        # TODO:
        # - Implement diff
        # - overwrite if different.

        if skip_download:
            return True
        if config is None:
            config = self.config
        if uri is None:
            if config:
                domain = config.get('provider', None)
            else:
                domain = None
            uri = self._get_provider_definition_uri(
                domain=domain)

        # XXX move to JSONConfig Fetcher
        request = self.fetcher.get(uri)
        request.raise_for_status()

        definition_file = os.path.join(
            baseconfig.get_default_provider_path(),
            baseconstants.DEFINITION_EXPECTED_PATH)

        folder, filename = os.path.split(definition_file)
        if not os.path.isdir(folder):
            mkdir_p(folder)
        with open(definition_file, 'wb') as f:
            f.write(json.dumps(request.json, indent=4))

    def fetch_eip_config(self, skip_download=False,
                         config=None, uri=None):
        if skip_download:
            return True
        if config is None:
            config = self.config
        if uri is None:
            if config:
                domain = config.get('provider', None)
            else:
                domain = None
            uri = self._get_eip_service_uri(
                domain=domain)

        # XXX move to JSONConfig Fetcher
        request = self.fetcher.get(uri)
        request.raise_for_status()

        definition_file = os.path.join(
            baseconfig.get_default_provider_path(),
            eipconstants.EIP_SERVICE_EXPECTED_PATH)

        folder, filename = os.path.split(definition_file)
        if not os.path.isdir(folder):
            mkdir_p(folder)
        with open(definition_file, 'wb') as f:
            f.write(json.dumps(request.json, indent=4))

    def check_complete_eip_config(self, config=None):
        if config is None:
            config = self.config
        try:
            'trying assertions'
            assert 'provider' in config
            assert config['provider'] is not None
        except AssertionError:
            raise eipexceptions.EIPConfigurationError

        # XXX TODO:
        # We should WRITE eip config if missing or
        # incomplete at this point

    def ping_gateway(self):
        raise NotImplementedError

    #
    # private helpers
    #

    def _get_default_eipconfig_path(self):
        return baseconfig.get_config_file(eipconstants.EIP_CONFIG)

    def _is_there_default_eipconfig(self):
        return os.path.isfile(
            self._get_default_eipconfig_path())

    def _dump_default_eipconfig(self):
        eipconfig.dump_default_eipconfig(
            self._get_default_eipconfig_path())

    def _get_provider_definition_uri(self, domain=None, path=None):
        if domain is None:
            domain = baseconstants.DEFAULT_TEST_PROVIDER
        if path is None:
            path = baseconstants.DEFINITION_EXPECTED_PATH
        return "https://%s/%s" % (domain, path)

    def _get_eip_service_uri(self, domain=None, path=None):
        if domain is None:
            domain = baseconstants.DEFAULT_TEST_PROVIDER
        if path is None:
            path = eipconstants.EIP_SERVICE_EXPECTED_PATH
        return "https://%s/%s" % (domain, path)

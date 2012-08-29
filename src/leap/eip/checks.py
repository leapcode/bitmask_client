import json
import logging
import os

logging.basicConfig()
logger = logging.getLogger(name=__name__)
logger.setLevel(logging.DEBUG)

import requests

from leap.base import config as baseconfig
from leap.base import constants as baseconstants
from leap.eip import config as eipconfig
from leap.eip import constants as eipconstants
from leap.eip import exceptions as eipexceptions
from leap.util.fileutil import mkdir_p

"""
EIPConfigChecker
----------
this is the first of 3 consecutive checks that we're implementing.

It is used from the eip conductor (a instance of EIPConnection that is
managed from the QtApp), running run_all method before trying to call
`connect` or any other of the state switching methods.

It checks that the needed files are provided or can be discovered over the
net. Much of these tests are not specific to EIP module, and can be splitted
into base.tests to be invoked by the base leap init routines.
However, I'm testing them alltogether for the sake of having the whole unit
reachable and testable as a whole.

Other related checkers - not implemented yet -:
* LeapNetworkChecker
* ProviderCertChecker
"""


class EIPConfigChecker(object):
    """
    Several tests needed
    to ensure a EIPConnection
    can be sucessfully established.
    use run_all to run all checks.
    """

    def __init__(self, fetcher=requests):
        # we do not want to accept too many
        # argument on init.
        # we want tests
        # to be explicitely run.
        self.config = None
        self.fetcher = fetcher

        self.eipconfig = eipconfig.EIPConfig()

    def run_all(self, checker=None, skip_download=False):
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
        checker.fetch_definition(skip_download=skip_download)
        checker.fetch_eip_config(skip_download=skip_download)
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
        logger.debug('checking default eip config')
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
        logger.debug('checking default provider')
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
        """
        fetches a definition file from server
        """
        # TODO:
        # - Implement diff
        # - overwrite if different.
        logger.debug('fetching definition')

        if skip_download:
            logger.debug('(fetching def skipped)')
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
            # XXX assert there is gateway !!
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
        #XXX
        return self.eipconfig.exists()
        #return os.path.isfile(
            #self._get_default_eipconfig_path())

    def _dump_default_eipconfig(self):
        #XXX self.eipconfig.save()
        logger.debug('saving eipconfig')
        #import ipdb;ipdb.set_trace()
        self.eipconfig.save()
        #eipconfig.dump_default_eipconfig(
            #self._get_default_eipconfig_path())

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

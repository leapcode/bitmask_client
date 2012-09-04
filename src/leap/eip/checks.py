import logging
import ssl
import os

import requests

from leap.base import constants as baseconstants
from leap.base import providers
from leap.eip import config as eipconfig
from leap.eip import constants as eipconstants
from leap.eip import exceptions as eipexceptions
from leap.eip import specs as eipspecs
from leap.util.fileutil import mkdir_p

logger = logging.getLogger(name=__name__)

"""
EIPConfigChecker
----------
this is the first of 3 consecutive checks that we're implementing.

It is used from the eip conductor (a instance of EIPConnection that is
managed from the QtApp), running `run_all` method before trying to call
`connect` or any other of the state-changing methods.

It checks that the needed files are provided or can be discovered over the
net. Much of these tests are not specific to EIP module, and can be splitted
into base.tests to be invoked by the base leap init routines.
However, I'm testing them alltogether for the sake of having the whole unit
reachable and testable as a whole.

Other related checkers - not implemented yet -:
* LeapNetworkChecker
"""


class LeapNetworkChecker(object):
    pass


class ProviderCertChecker(object):
    """
    Several checks needed for getting
    client certs and checking tls connection
    with provider.
    """
    def __init__(self, fetcher=requests):
        self.fetcher = fetcher
        self.cacert = None

    def run_all(self, checker=None, skip_download=False):
        if not checker:
            checker = self

        # For MVS+
        # checker.download_ca_cert()
        # checker.download_ca_signature()
        # checker.get_ca_signatures()
        # checker.is_there_trust_path()

        # For MVS
        checker.is_there_provider_ca()
        checker.is_https_working()
        checker.check_new_cert_needed()
        #checker.download_new_client_cert()

    def download_ca_cert(self):
        # MVS+
        raise NotImplementedError

    def download_ca_signature(self):
        # MVS+
        raise NotImplementedError

    def get_ca_signatures(self):
        # MVS+
        raise NotImplementedError

    def is_there_trust_path(self):
        # MVS+
        raise NotImplementedError

    def is_there_provider_ca(self):
        # XXX fake it till you make it! :P
        return True

        # enable this when we have
        # a custom "branded" bundle
        # certs package.
        try:
            from leap.custom import certs
        except ImportError:
            raise
        self.cacert = certs.where('cacert.pem')

    def is_https_working(self, uri=None, verify=True):
        # XXX raise InsecureURI or something better
        assert uri.startswith('https')
        if verify is True and self.cacert is not None:
            verify = self.cacert
        self.fetcher.get(uri, verify=verify)
        return True

    def check_new_cert_needed(self, skip_download=False):
        if not self.is_cert_valid(do_raise=False):
            self.download_new_client_cert(skip_download=skip_download)
            return True
        return False

    def download_new_client_cert(self, uri=None, verify=True,
                                 skip_download=False):
        if skip_download:
            return True
        if uri is None:
            uri = self._get_client_cert_uri()
        # XXX raise InsecureURI or something better
        assert uri.startswith('https')
        if verify is True and self.cacert is not None:
            verify = self.cacert
        req = self.fetcher.get(uri, verify=verify)
        pemfile_content = req.content
        self.is_valid_pemfile(pemfile_content)
        cert_path = self._get_client_cert_path()
        self.write_cert(pemfile_content, to=cert_path)
        return True

    def is_cert_valid(self, cert_path=None, do_raise=True):
        exists = lambda: self.is_certificate_exists()
        valid_pemfile = lambda: self.is_valid_pemfile()
        not_expired = lambda: self.is_cert_not_expired()
        #print 'exists?', exists
        #print 'valid', valid_pemfile
        #print 'not expired', not_expired

        valid = exists() and valid_pemfile() and not_expired()
        if not valid:
            if do_raise:
                raise Exception('missing cert')
            else:
                return False
        return True

    def is_certificate_exists(self, certfile=None):
        if certfile is None:
            certfile = self._get_client_cert_path()
        return os.path.isfile(certfile)

    def is_cert_not_expired(self):
        return True
        # XXX TODO
        # waiting on #507. If we're not using PyOpenSSL or anything alike
        # we will have to roll our own x509 parsing to extract time info.

    def is_valid_pemfile(self, cert_s=None):
        """
        checks that the passed string
        is a valid pem certificate
        @param cert_s: string containing pem content
        @type cert_s: string
        @rtype: bool
        """
        if cert_s is None:
            certfile = self._get_client_cert_path()
            with open(certfile) as cf:
                cert_s = cf.read()
        try:
            # XXX get a real cert validation
            # so far this is only checking begin/end
            # delimiters :)
            ssl.PEM_cert_to_DER_cert(cert_s)
        except:
            # XXX raise proper exception
            raise
        return True

    def _get_client_cert_uri(self):
        return "https://%s/cert/get" % (baseconstants.DEFAULT_TEST_PROVIDER)

    def _get_client_cert_path(self):
        # MVS+ : get provider path
        #import ipdb;ipdb.set_trace()
        return eipspecs.client_cert_path()

    def write_cert(self, pemfile_content, to=None):
        folder, filename = os.path.split(to)
        if not os.path.isdir(folder):
            mkdir_p(folder)
        with open(to, 'w') as cert_f:
            cert_f.write(pemfile_content)


class EIPConfigChecker(object):
    """
    Several checks needed
    to ensure a EIPConnection
    can be sucessfully established.
    use run_all to run all checks.
    """

    def __init__(self, fetcher=requests):
        # we do not want to accept too many
        # argument on init.
        # we want tests
        # to be explicitely run.
        self.fetcher = fetcher

        self.eipconfig = eipconfig.EIPConfig()
        self.defaultprovider = providers.LeapProviderDefinition()
        self.eipserviceconfig = eipconfig.EIPServiceConfig()

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
        # be enough. but here to make early tests easier.
        checker.check_default_eipconfig()

        checker.check_is_there_default_provider()
        checker.fetch_definition(skip_download=skip_download)
        checker.fetch_eip_service_config(skip_download=skip_download)
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
        if config is None:
            config = self.eipconfig.get_config()
        logger.debug('checking default provider')
        provider = config.get('provider', None)
        if provider is None:
            raise eipexceptions.EIPMissingDefaultProvider
        # XXX raise also if malformed ProviderDefinition?
        return True

    def fetch_definition(self, skip_download=False,
                         config=None, uri=None):
        """
        fetches a definition file from server
        """
        # TODO:
        # - Implement diff
        # - overwrite only if different.
        #   (attend to serial field different, for instance)

        logger.debug('fetching definition')

        if skip_download:
            logger.debug('(fetching def skipped)')
            return True
        if config is None:
            config = self.defaultprovider.get_config()
        if uri is None:
            domain = config.get('provider', None)
            uri = self._get_provider_definition_uri(domain=domain)

        self.defaultprovider.load(from_uri=uri, fetcher=self.fetcher)
        self.defaultprovider.save()

    def fetch_eip_service_config(self, skip_download=False,
                                 config=None, uri=None):
        if skip_download:
            return True
        if config is None:
            config = self.eipserviceconfig.get_config()
        if uri is None:
            domain = config.get('provider', None)
            uri = self._get_eip_service_uri(domain=domain)

        self.eipserviceconfig.load(from_uri=uri, fetcher=self.fetcher)
        self.eipserviceconfig.save()

    def check_complete_eip_config(self, config=None):
        # TODO check for gateway
        if config is None:
            config = self.eipconfig.get_config()
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

    def _is_there_default_eipconfig(self):
        return self.eipconfig.exists()

    def _dump_default_eipconfig(self):
        self.eipconfig.save()

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

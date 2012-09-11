from BaseHTTPServer import BaseHTTPRequestHandler
import copy
import json
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os
import urlparse

from StringIO import StringIO
from mock import (patch, Mock)

import ping
import requests

from leap.base import config as baseconfig
from leap.base.constants import (DEFAULT_PROVIDER_DEFINITION,
                                 DEFINITION_EXPECTED_PATH)
from leap.eip import checks as eipchecks
from leap.eip import specs as eipspecs
from leap.eip import exceptions as eipexceptions
from leap.eip.tests import data as testdata
from leap.testing.basetest import BaseLeapTest
from leap.testing.https_server import BaseHTTPSServerTestCase
from leap.testing.https_server import where as where_cert

_uid = os.getuid()


class NoLogRequestHandler:
    def log_message(self, *args):
        # don't write log msg to stderr
        pass

    def read(self, n=None):
        return ''


class LeapNetworkCheckTest(BaseLeapTest):
    # XXX to be moved to base.checks

    __name__ = "leap_network_check_tests"

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_checker_should_implement_check_methods(self):
        checker = eipchecks.LeapNetworkChecker()

        self.assertTrue(hasattr(checker, "test_internet_connection"),
                        "missing meth")
        self.assertTrue(hasattr(checker, "is_internet_up"),
                        "missing meth")
        self.assertTrue(hasattr(checker, "ping_gateway"),
                        "missing meth")

    def test_checker_should_actually_call_all_tests(self):
        checker = eipchecks.LeapNetworkChecker()

        mc = Mock()
        checker.run_all(checker=mc)
        self.assertTrue(mc.test_internet_connection.called, "not called")
        self.assertTrue(mc.ping_gateway.called, "not called")
        self.assertTrue(mc.is_internet_up.called,
                        "not called")

    def test_get_default_interface_no_interface(self):
        checker = eipchecks.LeapNetworkChecker()
        with patch('leap.eip.checks.open', create=True) as mock_open:
            with self.assertRaises(eipexceptions.NoDefaultInterfaceFoundError):
                mock_open.return_value = StringIO(
                    "Iface\tDestination Gateway\t"
                    "Flags\tRefCntd\tUse\tMetric\t"
                    "Mask\tMTU\tWindow\tIRTT")
                checker.get_default_interface_gateway()

    def test_ping_gateway_fail(self):
        checker = eipchecks.LeapNetworkChecker()
        with patch.object(ping, "quiet_ping") as mocked_ping:
            with self.assertRaises(eipexceptions.NoConnectionToGateway):
                mocked_ping.return_value = [11, "", ""]
                checker.ping_gateway("4.2.2.2")

    @unittest.skipUnless(_uid == 0, "root only")
    def test_ping_gateway(self):
        checker = eipchecks.LeapNetworkChecker()
        checker.ping_gateway("4.2.2.2")


class EIPCheckTest(BaseLeapTest):

    __name__ = "eip_check_tests"

    def setUp(self):
        pass

    def tearDown(self):
        pass

    # test methods are there, and can be called from run_all

    def test_checker_should_implement_check_methods(self):
        checker = eipchecks.EIPConfigChecker()

        self.assertTrue(hasattr(checker, "check_default_eipconfig"),
                        "missing meth")
        self.assertTrue(hasattr(checker, "check_is_there_default_provider"),
                        "missing meth")
        self.assertTrue(hasattr(checker, "fetch_definition"), "missing meth")
        self.assertTrue(hasattr(checker, "fetch_eip_service_config"),
                        "missing meth")
        self.assertTrue(hasattr(checker, "check_complete_eip_config"),
                        "missing meth")

    def test_checker_should_actually_call_all_tests(self):
        checker = eipchecks.EIPConfigChecker()

        mc = Mock()
        checker.run_all(checker=mc)
        self.assertTrue(mc.check_default_eipconfig.called, "not called")
        self.assertTrue(mc.check_is_there_default_provider.called,
                        "not called")
        self.assertTrue(mc.fetch_definition.called,
                        "not called")
        self.assertTrue(mc.fetch_eip_service_config.called,
                        "not called")
        self.assertTrue(mc.check_complete_eip_config.called,
                        "not called")
        #self.assertTrue(mc.ping_gateway.called,
                        #"not called")

    # test individual check methods

    def test_check_default_eipconfig(self):
        checker = eipchecks.EIPConfigChecker()
        # no eip config (empty home)
        eipconfig_path = checker.eipconfig.filename
        self.assertFalse(os.path.isfile(eipconfig_path))
        checker.check_default_eipconfig()
        # we've written one, so it should be there.
        self.assertTrue(os.path.isfile(eipconfig_path))
        with open(eipconfig_path, 'rb') as fp:
            deserialized = json.load(fp)

        # force re-evaluation of the paths
        # small workaround for evaluating home dirs correctly
        EIP_SAMPLE_JSON = copy.copy(testdata.EIP_SAMPLE_JSON)
        EIP_SAMPLE_JSON['openvpn_client_certificate'] = \
            eipspecs.client_cert_path()
        EIP_SAMPLE_JSON['openvpn_ca_certificate'] = \
            eipspecs.provider_ca_path()
        self.assertEqual(deserialized, EIP_SAMPLE_JSON)

        # TODO: shold ALSO run validation methods.

    def test_check_is_there_default_provider(self):
        checker = eipchecks.EIPConfigChecker()
        # we do dump a sample eip config, but lacking a
        # default provider entry.
        # This error will be possible catched in a different
        # place, when JSONConfig does validation of required fields.

        # passing direct config
        with self.assertRaises(eipexceptions.EIPMissingDefaultProvider):
            checker.check_is_there_default_provider(config={})

        # ok. now, messing with real files...
        # blank out default_provider
        sampleconfig = copy.copy(testdata.EIP_SAMPLE_JSON)
        sampleconfig['provider'] = None
        eipcfg_path = checker.eipconfig.filename
        with open(eipcfg_path, 'w') as fp:
            json.dump(sampleconfig, fp)
        with self.assertRaises(eipexceptions.EIPMissingDefaultProvider):
            checker.eipconfig.load(fromfile=eipcfg_path)
            checker.check_is_there_default_provider()

        sampleconfig = testdata.EIP_SAMPLE_JSON
        #eipcfg_path = checker._get_default_eipconfig_path()
        with open(eipcfg_path, 'w') as fp:
            json.dump(sampleconfig, fp)
        checker.eipconfig.load()
        self.assertTrue(checker.check_is_there_default_provider())

    def test_fetch_definition(self):
        with patch.object(requests, "get") as mocked_get:
            mocked_get.return_value.status_code = 200
            mocked_get.return_value.json = DEFAULT_PROVIDER_DEFINITION
            checker = eipchecks.EIPConfigChecker(fetcher=requests)
            sampleconfig = testdata.EIP_SAMPLE_JSON
            checker.fetch_definition(config=sampleconfig)

        fn = os.path.join(baseconfig.get_default_provider_path(),
                          DEFINITION_EXPECTED_PATH)
        with open(fn, 'r') as fp:
            deserialized = json.load(fp)
        self.assertEqual(DEFAULT_PROVIDER_DEFINITION, deserialized)

        # XXX TODO check for ConnectionError, HTTPError, InvalidUrl
        # (and proper EIPExceptions are raised).
        # Look at base.test_config.

    def test_fetch_eip_service_config(self):
        with patch.object(requests, "get") as mocked_get:
            mocked_get.return_value.status_code = 200
            mocked_get.return_value.json = testdata.EIP_SAMPLE_SERVICE
            checker = eipchecks.EIPConfigChecker(fetcher=requests)
            sampleconfig = testdata.EIP_SAMPLE_JSON
            checker.fetch_eip_service_config(config=sampleconfig)

    def test_check_complete_eip_config(self):
        checker = eipchecks.EIPConfigChecker()
        with self.assertRaises(eipexceptions.EIPConfigurationError):
            sampleconfig = copy.copy(testdata.EIP_SAMPLE_JSON)
            sampleconfig['provider'] = None
            checker.check_complete_eip_config(config=sampleconfig)
        with self.assertRaises(eipexceptions.EIPConfigurationError):
            sampleconfig = copy.copy(testdata.EIP_SAMPLE_JSON)
            del sampleconfig['provider']
            checker.check_complete_eip_config(config=sampleconfig)

        # normal case
        sampleconfig = copy.copy(testdata.EIP_SAMPLE_JSON)
        checker.check_complete_eip_config(config=sampleconfig)


class ProviderCertCheckerTest(BaseLeapTest):

    __name__ = "provider_cert_checker_tests"

    def setUp(self):
        pass

    def tearDown(self):
        pass

    # test methods are there, and can be called from run_all

    def test_checker_should_implement_check_methods(self):
        checker = eipchecks.ProviderCertChecker()

        # For MVS+
        self.assertTrue(hasattr(checker, "download_ca_cert"),
                        "missing meth")
        self.assertTrue(hasattr(checker, "download_ca_signature"),
                        "missing meth")
        self.assertTrue(hasattr(checker, "get_ca_signatures"), "missing meth")
        self.assertTrue(hasattr(checker, "is_there_trust_path"),
                        "missing meth")

        # For MVS
        self.assertTrue(hasattr(checker, "is_there_provider_ca"),
                        "missing meth")
        self.assertTrue(hasattr(checker, "is_https_working"), "missing meth")
        self.assertTrue(hasattr(checker, "check_new_cert_needed"),
                        "missing meth")

    def test_checker_should_actually_call_all_tests(self):
        checker = eipchecks.ProviderCertChecker()

        mc = Mock()
        checker.run_all(checker=mc)
        # XXX MVS+
        #self.assertTrue(mc.download_ca_cert.called, "not called")
        #self.assertTrue(mc.download_ca_signature.called, "not called")
        #self.assertTrue(mc.get_ca_signatures.called, "not called")
        #self.assertTrue(mc.is_there_trust_path.called, "not called")

        # For MVS
        self.assertTrue(mc.is_there_provider_ca.called, "not called")
        self.assertTrue(mc.is_https_working.called,
                        "not called")
        self.assertTrue(mc.check_new_cert_needed.called,
                        "not called")

    # test individual check methods

    def test_is_there_provider_ca(self):
        checker = eipchecks.ProviderCertChecker()
        self.assertTrue(
            checker.is_there_provider_ca())


class ProviderCertCheckerHTTPSTests(BaseHTTPSServerTestCase, BaseLeapTest):
    class request_handler(NoLogRequestHandler, BaseHTTPRequestHandler):
        responses = {
            '/': ['OK', ''],
            '/client.cert': [
                # XXX get sample cert
                '-----BEGIN CERTIFICATE-----',
                '-----END CERTIFICATE-----'],
            '/badclient.cert': [
                'BADCERT']}

        def do_GET(self):
            path = urlparse.urlparse(self.path)
            message = '\n'.join(self.responses.get(
                path.path, None))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(message)

    def test_is_https_working(self):
        fetcher = requests
        uri = "https://%s/" % (self.get_server())
        # bare requests call. this should just pass (if there is
        # an https service there).
        fetcher.get(uri, verify=False)
        checker = eipchecks.ProviderCertChecker(fetcher=fetcher)
        self.assertTrue(checker.is_https_working(uri=uri, verify=False))

        # for local debugs, when in doubt
        #self.assertTrue(checker.is_https_working(uri="https://github.com",
                        #verify=True))

        # for the two checks below, I know they fail because no ca
        # cert is passed to them, and I know that's the error that
        # requests return with our implementation.
        # We're receiving this because our
        # server is dying prematurely when the handshake is interrupted on the
        # client side.
        # Since we have access to the server, we could check that
        # the error raised has been:
        # SSL23_READ_BYTES: alert bad certificate
        with self.assertRaises(requests.exceptions.SSLError) as exc:
            fetcher.get(uri, verify=True)
            self.assertTrue(
                "SSL23_GET_SERVER_HELLO:unknown protocol" in exc.message)
        with self.assertRaises(requests.exceptions.SSLError) as exc:
            checker.is_https_working(uri=uri, verify=True)
            self.assertTrue(
                "SSL23_GET_SERVER_HELLO:unknown protocol" in exc.message)

        # get cacert from testing.https_server
        cacert = where_cert('cacert.pem')
        fetcher.get(uri, verify=cacert)
        self.assertTrue(checker.is_https_working(uri=uri, verify=cacert))

        # same, but get cacert from leap.custom
        # XXX TODO!

    def test_download_new_client_cert(self):
        uri = "https://%s/client.cert" % (self.get_server())
        cacert = where_cert('cacert.pem')
        checker = eipchecks.ProviderCertChecker()
        self.assertTrue(checker.download_new_client_cert(
                        uri=uri, verify=cacert))

        # now download a malformed cert
        uri = "https://%s/badclient.cert" % (self.get_server())
        cacert = where_cert('cacert.pem')
        checker = eipchecks.ProviderCertChecker()
        with self.assertRaises(ValueError):
            self.assertTrue(checker.download_new_client_cert(
                            uri=uri, verify=cacert))

        # did we write cert to its path?
        clientcertfile = eipspecs.client_cert_path()
        self.assertTrue(os.path.isfile(clientcertfile))
        certfile = eipspecs.client_cert_path()
        with open(certfile, 'r') as cf:
            certcontent = cf.read()
        self.assertEqual(certcontent,
                         '\n'.join(
                             self.request_handler.responses['/client.cert']))
        os.remove(clientcertfile)

    def test_is_cert_valid(self):
        checker = eipchecks.ProviderCertChecker()
        # TODO: better exception catching
        with self.assertRaises(Exception) as exc:
            self.assertFalse(checker.is_cert_valid())
            exc.message = "missing cert"

    def test_check_new_cert_needed(self):
        # check: missing cert
        checker = eipchecks.ProviderCertChecker()
        self.assertTrue(checker.check_new_cert_needed(skip_download=True))
        # TODO check: malformed cert
        # TODO check: expired cert
        # TODO check: pass test server uri instead of skip


if __name__ == "__main__":
    unittest.main()

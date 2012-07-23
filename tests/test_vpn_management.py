import unittest
import sys
import time

from eip_client.mocks.manager import get_openvpn_manager_mocks


class VPNManagerTests(unittest.TestCase):

    def setUp(self):
        self.manager = get_openvpn_manager_mocks()

    #
    # tests
    #

    def test_status_command(self):
        ret = self.manager.status()
        #print ret

    def test_connection_state(self):
        ts, status, ok, ip, remote = self.manager.get_connection_state()
        self.assertTrue(status in ('CONNECTED', 'DISCONNECTED'))
        self.assertTrue(isinstance(ts, time.struct_time))

    def test_status_io(self):
        when_ts, counters  = self.manager.get_status_io()
        self.assertTrue(isinstance(when_ts, time.struct_time))
        self.assertEqual(len(counters), 5)
        self.assertTrue(all(map(lambda x: x.isdigit(), counters)))


def test():
    suite = unittest.TestSuite()
    for cls in (VPNManagerTests,):
        suite.addTest(unittest.makeSuite(cls))
    runner = unittest.TextTestRunner(sys.stdout, verbosity=2,
                                         failfast=False)
    result = runner.run(suite)

if __name__ == "__main__":
    test()

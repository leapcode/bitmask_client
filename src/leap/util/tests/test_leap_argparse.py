from argparse import Namespace
import unittest

from leap.util import leap_argparse


class LeapArgParseTest(unittest.TestCase):
    """
    Test argparse options for eip client
    """

    def setUp(self):
        """
        get the parser
        """
        self.parser = leap_argparse.build_parser()

    def test_debug_mode(self):
        """
        test debug mode option
        """
        opts = self.parser.parse_args(
            ['--debug'])
        self.assertEqual(
            opts,
            Namespace(
                config_file=None,
                debug=True,
                log_file=None,
                openvpn_verb=None))

if __name__ == "__main__":
    unittest.main()

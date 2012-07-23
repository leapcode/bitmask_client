from argparse import Namespace
import unittest

from eip_client.utils import eip_argparse


class EIPArgParseTest(unittest.TestCase):
    """
    Test argparse options for eip client
    """

    def setUp(self):
        """
        get the parser
        """
        self.parser = eip_argparse.build_parser()

    def test_debug_mode(self):
        """
        test debug mode option
        """
        opts = self.parser.parse_args(
                ['--debug'])
        self.assertEqual(opts,
                Namespace(config=None,
                    debug=True))

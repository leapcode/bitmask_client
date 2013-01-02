import argparse


def build_parser():
    """
    all the options for the leap arg parser
    Some of these could be switched on only if debug flag is present!
    """
    epilog = "Copyright 2012 The Leap Project"
    parser = argparse.ArgumentParser(description="""
Launches main LEAP Client""", epilog=epilog)
    parser.add_argument('-d', '--debug', action="store_true",
                        help='launches in debug mode')
    parser.add_argument('-c', '--config', metavar="CONFIG FILE", nargs='?',
                        action="store", dest="config_file",
                        type=argparse.FileType('r'),
                        help='optional config file')
    parser.add_argument('--logfile', metavar="LOG FILE", nargs='?',
                        action="store", dest="log_file",
                        #type=argparse.FileType('w'),
                        help='optional log file')
    parser.add_argument('--openvpn-verbosity', nargs='?',
                        type=int,
                        action="store", dest="openvpn_verb",
                        help='verbosity level for openvpn logs [1-6]')
    parser.add_argument('-l', '--no-provider-checks',
                        action="store_true", default=False,
                        help="skips download of provider config files. gets "
                        "config from local files only. Will fail if cannot "
                        "find any")
    parser.add_argument('-k', '--no-ca-verify',
                        action="store_true", default=False,
                        help="(insecure). Skips verification of the server "
                        "certificate used in TLS handshake.")
    return parser


def init_leapc_args():
    parser = build_parser()
    opts, unknown = parser.parse_known_args()
    return parser, opts

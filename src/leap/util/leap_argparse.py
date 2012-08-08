import argparse


def build_parser():
    epilog = "Copyright 2012 The Leap Project"
    parser = argparse.ArgumentParser(description="""
Launches main LEAP Client""", epilog=epilog)
    parser.add_argument('--debug', action="store_true",
                        help='launches in debug mode')
    parser.add_argument('--config', metavar="CONFIG FILE", nargs='?',
                        action="store", dest="config_file",
                        type=argparse.FileType('r'),
                        help='optional config file')
    return parser


def init_leapc_args():
    parser = build_parser()
    opts = parser.parse_args()
    return parser, opts

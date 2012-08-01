import ConfigParser
import os

from leap.util.fileutil import which, mkdir_p


def get_sensible_defaults():
    """
    gathers a dict of sensible defaults,
    platform sensitive,
    to be used to initialize the config parser
    """
    defaults = dict()
    defaults['openvpn_binary'] = which('openvpn')
    return defaults


def get_config(config_file=None):
    """
    temporary method for getting configs,
    mainly for early stage development process.
    in the future we will get preferences
    from the storage api
    """
    # TODO
    # - refactor out common things and get
    # them to util/ or baseapp/

    defaults = get_sensible_defaults()
    config = ConfigParser.ConfigParser(defaults)

    if not config_file:
        fpath = os.path.expanduser('~/.config/leap/eip.cfg')
        if not os.path.isfile(fpath):
            dpath, cfile = os.path.split(fpath)
            if not os.path.isdir(dpath):
                mkdir_p(dpath)
            with open(fpath, 'wb') as configfile:
                config.write(configfile)
        config_file = open(fpath)

    #TODO
    # - get a more sensible path for win/mac
    # - convert config_file to list;
    #   look in places like /etc/leap/eip.cfg
    #   for global settings.
    # - raise warnings/error if bad options.

    try:
        config.readfp(config_file)
    except:
        # XXX no file exists?
        raise
    return config


# XXX wrapper around config? to get default values
def get_with_defaults(config, section, option):
    # XXX REMOVE ME
    if config.has_option(section, option):
        return config.get(section, option)
    else:
        # XXX lookup in defaults dict???
        pass


def get_vpn_stdout_mockup():
    # XXX REMOVE ME
    command = "python"
    args = ["-u", "-c", "from eip_client import fakeclient;\
fakeclient.write_output()"]
    return command, args

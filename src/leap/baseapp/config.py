import ConfigParser
import os


def get_config(config_file=None):
    """
    temporary method for getting configs,
    mainly for early stage development process.
    in the future we will get preferences
    from the storage api
    """
    config = ConfigParser.ConfigParser()
    #config.readfp(open('defaults.cfg'))
    #XXX does this work on win / mac also???
    conf_path_list = ['eip.cfg',  # XXX build a
                      # proper path with platform-specific places
                      # XXX make .config/foo
                      os.path.expanduser('~/.eip.cfg')]
    if config_file:
        config.readfp(config_file)
    else:
        config.read(conf_path_list)
    return config


# XXX wrapper around config? to get default values

def get_with_defaults(config, section, option):
    if config.has_option(section, option):
        return config.get(section, option)
    else:
        # XXX lookup in defaults dict???
        pass


def get_vpn_stdout_mockup():
    command = "python"
    args = ["-u", "-c", "from eip_client import fakeclient;\
fakeclient.write_output()"]
    return command, args

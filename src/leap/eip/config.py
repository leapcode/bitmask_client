import ConfigParser
import grp
import os
import platform

from leap.util.fileutil import which, mkdir_p
from leap.baseapp.permcheck import is_pkexec_in_system


class EIPNoPkexecAvailable(Exception):
    pass


def build_ovpn_options(daemon=False):
    """
    build a list of options
    to be passed in the
    openvpn invocation
    @rtype: list
    @rparam: options
    """
    # XXX review which of the
    # options we don't need.

    # TODO pass also the config file,
    # since we will need to take some
    # things from there if present.

    # get user/group name
    # also from config.
    user = os.getlogin()
    gid = os.getgroups()[-1]
    group = grp.getgrgid(gid).gr_name

    opts = []
    opts.append('--persist-tun')

    # set user and group
    opts.append('--user')
    opts.append('%s' % user)
    opts.append('--group')
    opts.append('%s' % group)

    opts.append('--management-client-user')
    opts.append('%s' % user)
    opts.append('--management-signal')

    # set default options for management
    # interface. unix sockets or telnet interface for win.
    # XXX take them from the config object.

    ourplatform = platform.system()
    if ourplatform in ("Linux", "Mac"):
        opts.append('--management')
        opts.append('/tmp/.eip.sock')
        opts.append('unix')
    if ourplatform == "Windows":
        opts.append('--management')
        opts.append('localhost')
        # XXX which is a good choice?
        opts.append('7777')

    # remaining config options, in a file
    # NOTE: we will build this file from
    # the service definition file.
    ovpncnf = os.path.expanduser(
        '~/.config/leap/openvpn.conf')
    opts.append('--config')
    opts.append(ovpncnf)

    # we cannot run in daemon mode
    # with the current subp setting.
    # see: https://leap.se/code/issues/383
    #if daemon is True:
    #    opts.append('--daemon')

    return opts


def build_ovpn_command(config, debug=False):
    """
    build a string with the
    complete openvpn invocation

    @param config: config object
    @type config: ConfigParser instance

    @rtype [string, [list of strings]]
    @rparam: a list containing the command string
        and a list of options.
    """
    command = []
    use_pkexec = True
    ovpn = None

    if config.has_option('openvpn', 'use_pkexec'):
        use_pkexec = config.get('openvpn', 'use_pkexec')
    if platform.system() == "Linux" and use_pkexec:

        # XXX check for both pkexec (done)
        # AND a suitable authentication
        # agent running.

        if not is_pkexec_in_system():
            raise EIPNoPkexecAvailable

        #TBD --
        #if not is_auth_agent_running()
        # raise EIPNoPolkitAuthAgentAvailable

        command.append('pkexec')

    if config.has_option('openvpn',
                         'openvpn_binary'):
        ovpn = config.get('openvpn',
                          'openvpn_binary')
    if not ovpn and config.has_option('DEFAULT',
                                      'openvpn_binary'):
        ovpn = config.get('DEFAULT',
                          'openvpn_binary')

    if ovpn:
        command.append(ovpn)

    daemon_mode = not debug

    for opt in build_ovpn_options(daemon=daemon_mode):
        command.append(opt)

    # XXX check len and raise proper error

    return [command[0], command[1:]]


def get_sensible_defaults():
    """
    gathers a dict of sensible defaults,
    platform sensitive,
    to be used to initialize the config parser
    @rtype: dict
    @rparam: default options.
    """

    # this way we're passing a simple dict
    # that will initialize the configparser
    # and will get written to "DEFAULTS" section,
    # which is fine for now.
    # if we want to write to a particular section
    # we can better pass a tuple of triples
    # (('section1', 'foo', '23'),)
    # and config.set them

    defaults = dict()
    defaults['openvpn_binary'] = which('openvpn')
    defaults['autostart'] = 'true'

    # TODO
    # - management.
    return defaults


def get_config(config_file=None):
    """
    temporary method for getting configs,
    mainly for early stage development process.
    in the future we will get preferences
    from the storage api

    @rtype: ConfigParser instance
    @rparam: a config object
    """
    # TODO
    # - refactor out common things and get
    # them to util/ or baseapp/

    defaults = get_sensible_defaults()
    config = ConfigParser.ConfigParser(defaults)

    if not config_file:
        fpath = os.path.expanduser(
            '~/.config/leap/eip.cfg')
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

    # at this point, the file should exist.
    # errors would have been raised above.
    config.readfp(config_file)

    return config

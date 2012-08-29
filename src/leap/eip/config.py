import ConfigParser  # to be deprecated
import json
import logging
import os
import platform
import socket

from leap.util.fileutil import (which, mkdir_p,
                                check_and_fix_urw_only)

from leap.base import config as baseconfig
from leap.baseapp.permcheck import (is_pkexec_in_system,
                                    is_auth_agent_running)
from leap.eip import exceptions as eip_exceptions
from leap.eip import constants as eipconstants
from leap.eip import specs as eipspecs

logging.basicConfig()
logger = logging.getLogger(name=__name__)
logger.setLevel('DEBUG')


class EIPConfig(baseconfig.JSONLeapConfig):
    spec = eipspecs.eipconfig_spec

    def _get_slug(self):
        return baseconfig.get_config_file('eip.json')

    def _set_slug(self, *args, **kwargs):
        raise AttributeError("you cannot set slug")

    slug = property(_get_slug, _set_slug)


class EIPServiceConfig(baseconfig.JSONLeapConfig):
    spec = eipspecs.eipservice_config_spec

    def _get_slug(self):
        return baseconfig.get_config_file(
            'eip-service.json',
            folder=baseconfig.get_default_provider_path())

    def _set_slug(self):
        raise AttributeError("you cannot set slug")

    slug = property(_get_slug, _set_slug)


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
    user = baseconfig.get_username()
    group = baseconfig.get_groupname()

    opts = []

    opts.append('--client')

    opts.append('--dev')
    # XXX same in win?
    opts.append('tun')
    opts.append('--persist-tun')
    opts.append('--persist-key')

    # remote
    # XXX get remote from eip.json
    opts.append('--remote')
    opts.append('testprovider.example.org')
    opts.append('1194')
    opts.append('udp')

    opts.append('--tls-client')
    opts.append('--remote-cert-tls')
    opts.append('server')

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
        # XXX get a different sock each time ...
        opts.append('/tmp/.eip.sock')
        opts.append('unix')
    if ourplatform == "Windows":
        opts.append('--management')
        opts.append('localhost')
        # XXX which is a good choice?
        opts.append('7777')

    # certs
    opts.append('--cert')
    opts.append(eipspecs.client_cert_path())
    opts.append('--key')
    opts.append(eipspecs.client_cert_path())
    opts.append('--ca')
    opts.append(eipspecs.provider_ca_path())

    # we cannot run in daemon mode
    # with the current subp setting.
    # see: https://leap.se/code/issues/383
    #if daemon is True:
        #opts.append('--daemon')

    return opts


def build_ovpn_command(config, debug=False, do_pkexec_check=True):
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
    if platform.system() == "Linux" and use_pkexec and do_pkexec_check:

        # XXX check for both pkexec (done)
        # AND a suitable authentication
        # agent running.
        logger.info('use_pkexec set to True')

        if not is_pkexec_in_system():
            logger.error('no pkexec in system')
            raise eip_exceptions.EIPNoPkexecAvailable

        if not is_auth_agent_running():
            logger.warning(
                "no polkit auth agent found. "
                "pkexec will use its own text "
                "based authentication agent. "
                "that's probably a bad idea")
            raise eip_exceptions.EIPNoPolkitAuthAgentAvailable

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
        vpn_command = ovpn
    else:
        vpn_command = "openvpn"

    command.append(vpn_command)

    daemon_mode = not debug

    for opt in build_ovpn_options(daemon=daemon_mode):
        command.append(opt)

    # XXX check len and raise proper error

    return [command[0], command[1:]]


# XXX deprecate
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


# XXX to be deprecated. see dump_default_eipconfig
# and the new JSONConfig classes.
def get_config(config_file=None):
    """
    temporary method for getting configs,
    mainly for early stage development process.
    in the future we will get preferences
    from the storage api

    @rtype: ConfigParser instance
    @rparam: a config object
    """
    defaults = get_sensible_defaults()
    config = ConfigParser.ConfigParser(defaults)

    if not config_file:
        fpath = baseconfig.get_config_file('eip.cfg')
        if not os.path.isfile(fpath):
            dpath, cfile = os.path.split(fpath)
            if not os.path.isdir(dpath):
                mkdir_p(dpath)
            with open(fpath, 'wb') as configfile:
                config.write(configfile)
        config_file = open(fpath)
    config.readfp(config_file)
    return config


def dump_default_eipconfig(filepath):
    """
    writes a sample eip config
    in the given location
    """
    # XXX TODO:
    # use EIPConfigSpec istead
    folder, filename = os.path.split(filepath)
    if not os.path.isdir(folder):
        mkdir_p(folder)
    with open(filepath, 'w') as fp:
        json.dump(eipconstants.EIP_SAMPLE_JSON, fp)


def check_vpn_keys(config):
    """
    performs an existance and permission check
    over the openvpn keys file.
    Currently we're expecting a single file
    per provider, containing the CA cert,
    the provider key, and our client certificate
    """

    keyopt = ('provider', 'keyfile')

    # XXX at some point,
    # should separate between CA, provider cert
    # and our certificate.
    # make changes in the default provider template
    # accordingly.

    # get vpn keys
    if config.has_option(*keyopt):
        keyfile = config.get(*keyopt)
    else:
        keyfile = baseconfig.get_config_file(
            'openvpn.keys',
            folder=baseconfig.get_default_provider_path())
        logger.debug('keyfile = %s', keyfile)

    # if no keys, raise error.
    # should be catched by the ui and signal user.

    if not os.path.isfile(keyfile):
        logger.error('key file %s not found. aborting.',
                     keyfile)
        raise eip_exceptions.EIPInitNoKeyFileError

    # check proper permission on keys
    # bad perms? try to fix them
    try:
        check_and_fix_urw_only(keyfile)
    except OSError:
        raise eip_exceptions.EIPInitBadKeyFilePermError

import logging
import os
import platform
import re
import tempfile

from leap import __branding as BRANDING
from leap import certs
from leap.util.misc import null_check
from leap.util.fileutil import (which, mkdir_p, check_and_fix_urw_only)

from leap.base import config as baseconfig
from leap.baseapp.permcheck import (is_pkexec_in_system,
                                    is_auth_agent_running)
from leap.eip import exceptions as eip_exceptions
from leap.eip import specs as eipspecs

logger = logging.getLogger(name=__name__)
provider_ca_file = BRANDING.get('provider_ca_file', None)

_platform = platform.system()


class EIPConfig(baseconfig.JSONLeapConfig):
    spec = eipspecs.eipconfig_spec

    def _get_slug(self):
        eipjsonpath = baseconfig.get_config_file(
            'eip.json')
        return eipjsonpath

    def _set_slug(self, *args, **kwargs):
        raise AttributeError("you cannot set slug")

    slug = property(_get_slug, _set_slug)


class EIPServiceConfig(baseconfig.JSONLeapConfig):
    spec = eipspecs.eipservice_config_spec

    def _get_slug(self):
        domain = getattr(self, 'domain', None)
        if domain:
            path = baseconfig.get_provider_path(domain)
        else:
            path = baseconfig.get_default_provider_path()
        return baseconfig.get_config_file(
            'eip-service.json', folder=path)

    def _set_slug(self):
        raise AttributeError("you cannot set slug")

    slug = property(_get_slug, _set_slug)


def get_socket_path():
    socket_path = os.path.join(
        tempfile.mkdtemp(prefix="leap-tmp"),
        'openvpn.socket')
    #logger.debug('socket path: %s', socket_path)
    return socket_path


def get_eip_gateway(eipconfig=None, eipserviceconfig=None):
    """
    return the first host in eip service config
    that matches the name defined in the eip.json config
    file.
    """
    # XXX eventually we should move to a more clever
    # gateway selection. maybe we could return
    # all gateways that match our cluster.

    null_check(eipconfig, "eipconfig")
    null_check(eipserviceconfig, "eipserviceconfig")
    PLACEHOLDER = "testprovider.example.org"

    conf = eipconfig.config
    eipsconf = eipserviceconfig.config

    primary_gateway = conf.get('primary_gateway', None)
    if not primary_gateway:
        return PLACEHOLDER

    gateways = eipsconf.get('gateways', None)
    if not gateways:
        logger.error('missing gateways in eip service config')
        return PLACEHOLDER

    if len(gateways) > 0:
        for gw in gateways:
            clustername = gw.get('cluster', None)
            if not clustername:
                logger.error('no cluster name')
                return

            if clustername == primary_gateway:
                # XXX at some moment, we must
                # make this a more generic function,
                # and return ports, protocols...
                ipaddress = gw.get('ip_address', None)
                if not ipaddress:
                    logger.error('no ip_address')
                    return
                return ipaddress
    logger.error('could not find primary gateway in provider'
                 'gateway list')


def get_cipher_options(eipserviceconfig=None):
    """
    gathers optional cipher options from eip-service config.
    :param eipserviceconfig: EIPServiceConfig instance
    """
    null_check(eipserviceconfig, 'eipserviceconfig')
    eipsconf = eipserviceconfig.get_config()

    ALLOWED_KEYS = ("auth", "cipher", "tls-cipher")
    CIPHERS_REGEX = re.compile("[A-Z0-9\-]+")
    opts = []
    if 'openvpn_configuration' in eipsconf:
        config = eipserviceconfig.config.get(
            "openvpn_configuration", {})
        for key, value in config.items():
            if key in ALLOWED_KEYS and value is not None:
                sanitized_val = CIPHERS_REGEX.findall(value)
                if len(sanitized_val) != 0:
                    _val = sanitized_val[0]
                    opts.append('--%s' % key)
                    opts.append('%s' % _val)
    return opts


def build_ovpn_options(daemon=False, socket_path=None, **kwargs):
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

    provider = kwargs.pop('provider', None)
    eipconfig = EIPConfig(domain=provider)
    eipconfig.load()
    eipserviceconfig = EIPServiceConfig(domain=provider)
    eipserviceconfig.load()

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

    verbosity = kwargs.get('ovpn_verbosity', None)
    if verbosity and 1 <= verbosity <= 6:
        opts.append('--verb')
        opts.append("%s" % verbosity)

    # remote ##############################
    # (server, port, protocol)

    opts.append('--remote')

    gw = get_eip_gateway(eipconfig=eipconfig,
                         eipserviceconfig=eipserviceconfig)
    logger.debug('setting eip gateway to %s', gw)
    opts.append(str(gw))

    # get port/protocol from eipservice too
    opts.append('1194')
    #opts.append('80')
    opts.append('udp')

    opts.append('--tls-client')
    opts.append('--remote-cert-tls')
    opts.append('server')

    # get ciphers #######################

    ciphers = get_cipher_options(
        eipserviceconfig=eipserviceconfig)
    for cipheropt in ciphers:
        opts.append(str(cipheropt))

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

    if _platform == "Windows":
        opts.append('--management')
        opts.append('localhost')
        # XXX which is a good choice?
        opts.append('7777')

    if _platform in ("Linux", "Darwin"):
        opts.append('--management')

        if socket_path is None:
            socket_path = get_socket_path()
        opts.append(socket_path)
        opts.append('unix')

        opts.append('--script-security')
        opts.append('2')

    if _platform == "Linux":
        opts.append("--up")
        opts.append("/etc/openvpn/update-resolv-conf")
        opts.append("--down")
        opts.append("/etc/openvpn/update-resolv-conf")

    # certs
    client_cert_path = eipspecs.client_cert_path(provider)
    ca_cert_path = eipspecs.provider_ca_path(provider)

    # XXX FIX paths for MAC
    opts.append('--cert')
    opts.append(client_cert_path)
    opts.append('--key')
    opts.append(client_cert_path)
    opts.append('--ca')
    opts.append(ca_cert_path)

    # we cannot run in daemon mode
    # with the current subp setting.
    # see: https://leap.se/code/issues/383
    #if daemon is True:
        #opts.append('--daemon')

    logger.debug('vpn options: %s', ' '.join(opts))
    return opts


def build_ovpn_command(debug=False, do_pkexec_check=True, vpnbin=None,
                       socket_path=None, **kwargs):
    """
    build a string with the
    complete openvpn invocation

    @rtype [string, [list of strings]]
    @rparam: a list containing the command string
        and a list of options.
    """
    command = []
    use_pkexec = True
    ovpn = None

    # XXX get use_pkexec from config instead.

    if _platform == "Linux" and use_pkexec and do_pkexec_check:

        # check for both pkexec
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

    if vpnbin is None:
        if _platform == "Darwin":
            # XXX Should hardcode our installed path
            # /Applications/LEAPClient.app/Contents/Resources/openvpn.leap
            openvpn_bin = "openvpn.leap"
        else:
            openvpn_bin = "openvpn"
        #XXX hardcode for darwin
        ovpn = which(openvpn_bin)
    else:
        ovpn = vpnbin
    if ovpn:
        vpn_command = ovpn
    else:
        vpn_command = "openvpn"
    command.append(vpn_command)
    daemon_mode = not debug

    for opt in build_ovpn_options(daemon=daemon_mode, socket_path=socket_path,
                                  **kwargs):
        command.append(opt)

    # XXX check len and raise proper error

    if _platform == "Darwin":
        OSX_ASADMIN = 'do shell script "%s" with administrator privileges'
        # XXX fix workaround for Nones
        _command = [x if x else " " for x in command]
        # XXX debugging!
        # XXX get openvpn log path from debug flags
        _command.append('--log')
        _command.append('/tmp/leap_openvpn.log')
        return ["osascript", ["-e", OSX_ASADMIN % ' '.join(_command)]]
    else:
        return [command[0], command[1:]]


def check_vpn_keys(provider=None):
    """
    performs an existance and permission check
    over the openvpn keys file.
    Currently we're expecting a single file
    per provider, containing the CA cert,
    the provider key, and our client certificate
    """
    assert provider is not None
    provider_ca = eipspecs.provider_ca_path(provider)
    client_cert = eipspecs.client_cert_path(provider)

    logger.debug('provider ca = %s', provider_ca)
    logger.debug('client cert = %s', client_cert)

    # if no keys, raise error.
    # it's catched by the ui and signal user.

    if not os.path.isfile(provider_ca):
        # not there. let's try to copy.
        folder, filename = os.path.split(provider_ca)
        if not os.path.isdir(folder):
            mkdir_p(folder)
        if provider_ca_file:
            cacert = certs.where(provider_ca_file)
        with open(provider_ca, 'w') as pca:
            with open(cacert, 'r') as cac:
                pca.write(cac.read())

    if not os.path.isfile(provider_ca):
        logger.error('key file %s not found. aborting.',
                     provider_ca)
        raise eip_exceptions.EIPInitNoKeyFileError

    if not os.path.isfile(client_cert):
        logger.error('key file %s not found. aborting.',
                     client_cert)
        raise eip_exceptions.EIPInitNoKeyFileError

    for keyfile in (provider_ca, client_cert):
        # bad perms? try to fix them
        try:
            check_and_fix_urw_only(keyfile)
        except OSError:
            raise eip_exceptions.EIPInitBadKeyFilePermError

# -*- coding: utf-8 -*-
# vpnprocess.py
# Copyright (C) 2013 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
VPN Manager, spawned in a custom processProtocol.
"""
import commands
import logging
import os
import shutil
import socket
import subprocess
import sys

from itertools import chain, repeat

import psutil
try:
    # psutil < 2.0.0
    from psutil.error import AccessDenied as psutil_AccessDenied
    PSUTIL_2 = False
except ImportError:
    # psutil >= 2.0.0
    from psutil import AccessDenied as psutil_AccessDenied
    PSUTIL_2 = True

from leap.bitmask.config import flags
from leap.bitmask.config.providerconfig import ProviderConfig
from leap.bitmask.services.eip import get_vpn_launcher
from leap.bitmask.services.eip import linuxvpnlauncher
from leap.bitmask.services.eip.eipconfig import EIPConfig
from leap.bitmask.services.eip.udstelnet import UDSTelnet
from leap.bitmask.util import first, force_eval
from leap.bitmask.platform_init import IS_MAC, IS_LINUX
from leap.common.check import leap_assert, leap_assert_type

logger = logging.getLogger(__name__)
vpnlog = logging.getLogger('leap.openvpn')

from twisted.internet import defer, protocol, reactor
from twisted.internet import error as internet_error
from twisted.internet.task import LoopingCall


class VPNObserver(object):
    """
    A class containing different patterns in the openvpn output that
    we can react upon.
    """

    # TODO this is i18n-sensitive, right?
    # in that case, we should add the translations :/
    # until we find something better.

    _events = {
        'NETWORK_UNREACHABLE': (
            'Network is unreachable (code=101)',),
        'PROCESS_RESTART_TLS': (
            "SIGTERM[soft,tls-error]",),
        'PROCESS_RESTART_PING': (
            "SIGTERM[soft,ping-restart]",),
        'INITIALIZATION_COMPLETED': (
            "Initialization Sequence Completed",),
    }

    def __init__(self, signaler=None):
        self._signaler = signaler

    def watch(self, line):
        """
        Inspects line searching for the different patterns. If a match
        is found, try to emit the corresponding signal.

        :param line: a line of openvpn output
        :type line: str
        """
        chained_iter = chain(*[
            zip(repeat(key, len(l)), l)
            for key, l in self._events.iteritems()])
        for event, pattern in chained_iter:
            if pattern in line:
                logger.debug('pattern matched! %s' % pattern)
                break
        else:
            return

        sig = self._get_signal(event)
        if sig is not None:
            self._signaler.signal(sig)
            return
        else:
            logger.debug('We got %s event from openvpn output but we could '
                         'not find a matching signal for it.' % event)

    def _get_signal(self, event):
        """
        Tries to get the matching signal from the eip signals
        objects based on the name of the passed event (in lowercase)

        :param event: the name of the event that we want to get a signal for
        :type event: str
        :returns: a Signaler signal or None
        :rtype: str or None
        """
        sig = self._signaler
        signals = {
            "network_unreachable": sig.eip_network_unreachable,
            "process_restart_tls": sig.eip_process_restart_tls,
            "process_restart_ping": sig.eip_process_restart_ping,
            "initialization_completed": sig.eip_connected
        }
        return signals.get(event.lower())


class OpenVPNAlreadyRunning(Exception):
    message = ("Another openvpn instance is already running, and could "
               "not be stopped.")


class AlienOpenVPNAlreadyRunning(Exception):
    message = ("Another openvpn instance is already running, and could "
               "not be stopped because it was not launched by LEAP.")


class VPN(object):
    """
    This is the high-level object that the GUI is dealing with.
    It exposes the start and terminate methods.

    On start, it spawns a VPNProcess instance that will use a vpnlauncher
    suited for the running platform and connect to the management interface
    opened by the openvpn process, executing commands over that interface on
    demand.
    """
    TERMINATE_MAXTRIES = 10
    TERMINATE_WAIT = 1  # secs

    OPENVPN_VERB = "openvpn_verb"

    def __init__(self, **kwargs):
        """
        Instantiate empty attributes and get a copy
        of a QObject containing the QSignals that we will pass along
        to the VPNManager.
        """
        self._vpnproc = None
        self._pollers = []

        self._signaler = kwargs['signaler']
        self._openvpn_verb = flags.OPENVPN_VERBOSITY

        self._user_stopped = False

    def start(self, *args, **kwargs):
        """
        Starts the openvpn subprocess.

        :param args: args to be passed to the VPNProcess
        :type args: tuple

        :param kwargs: kwargs to be passed to the VPNProcess
        :type kwargs: dict
        """
        logger.debug('VPN: start')
        self._user_stopped = False
        self._stop_pollers()
        kwargs['openvpn_verb'] = self._openvpn_verb
        kwargs['signaler'] = self._signaler

        restart = kwargs.pop('restart', False)

        # start the main vpn subprocess
        vpnproc = VPNProcess(*args, **kwargs)

        if vpnproc.get_openvpn_process():
            logger.info("Another vpn process is running. Will try to stop it.")
            vpnproc.stop_if_already_running()

        # we try to bring the firewall up
        if IS_LINUX:
            gateways = vpnproc.getGateways()
            firewall_up = self._launch_firewall(gateways,
                                                restart=restart)
            if not restart and not firewall_up:
                logger.error("Could not bring firewall up, "
                             "aborting openvpn launch.")
                return

        # FIXME it would be good to document where the
        # errors here are catched, since we currently handle them
        # at the frontend layer. This *should* move to be handled entirely
        # in the backend.
        # exception is indeed technically catched in backend, then converted
        # into a signal, that is catched in the eip_status widget in the
        # frontend, and converted into a signal to abort the connection that is
        # sent to the backend again.

        # the whole exception catching should be done in the backend, without
        # the ping-pong to the frontend, and without adding any logical checks
        # in the frontend. We should just communicate UI changes to frontend,
        # and abstract us away from anything else.
        try:
            cmd = vpnproc.getCommand()
        except Exception as e:
            logger.error("Error while getting vpn command... {0!r}".format(e))
            raise

        env = os.environ
        for key, val in vpnproc.vpn_env.items():
            env[key] = val

        reactor.spawnProcess(vpnproc, cmd[0], cmd, env)
        self._vpnproc = vpnproc

        # add pollers for status and state
        # this could be extended to a collection of
        # generic watchers

        poll_list = [LoopingCall(vpnproc.pollStatus),
                     LoopingCall(vpnproc.pollState)]
        self._pollers.extend(poll_list)
        self._start_pollers()

    def _launch_firewall(self, gateways, restart=False):
        """
        Launch the firewall using the privileged wrapper.

        :param gateways:
        :type gateways: list

        :returns: True if the exitcode of calling the root helper in a
                  subprocess is 0.
        :rtype: bool
        """
        # XXX could check for wrapper existence, check it's root owned etc.
        # XXX could check that the iptables rules are in place.

        BM_ROOT = force_eval(linuxvpnlauncher.LinuxVPNLauncher.BITMASK_ROOT)
        cmd = ["pkexec", BM_ROOT, "firewall", "start"]
        if restart:
            cmd.append("restart")
        exitCode = subprocess.call(cmd + gateways)
        return True if exitCode is 0 else False

    def is_fw_down(self):
        """
        Return whether the firewall is down or not.

        :rtype: bool
        """
        BM_ROOT = force_eval(linuxvpnlauncher.LinuxVPNLauncher.BITMASK_ROOT)
        fw_up_cmd = "pkexec {0} firewall isup".format(BM_ROOT)
        fw_is_down = lambda: commands.getstatusoutput(fw_up_cmd)[0] == 256
        return fw_is_down()

    def tear_down_firewall(self):
        """
        Tear the firewall down using the privileged wrapper.
        """
        if IS_MAC:
            # We don't support Mac so far
            return True
        BM_ROOT = force_eval(linuxvpnlauncher.LinuxVPNLauncher.BITMASK_ROOT)
        exitCode = subprocess.call(["pkexec",
                                    BM_ROOT, "firewall", "stop"])
        return True if exitCode is 0 else False

    def bitmask_root_vpn_down(self):
        """
        Bring openvpn down using the privileged wrapper.
        """
        if IS_MAC:
            # We don't support Mac so far
            return True
        BM_ROOT = force_eval(linuxvpnlauncher.LinuxVPNLauncher.BITMASK_ROOT)
        exitCode = subprocess.call(["pkexec",
                                    BM_ROOT, "openvpn", "stop"])
        return True if exitCode is 0 else False

    def _kill_if_left_alive(self, tries=0):
        """
        Check if the process is still alive, and send a
        SIGKILL after a timeout period.

        :param tries: counter of tries, used in recursion
        :type tries: int
        """
        while tries < self.TERMINATE_MAXTRIES:
            if self._vpnproc.transport.pid is None:
                logger.debug("Process has been happily terminated.")

                # we try to tear the firewall down
                if IS_LINUX and self._user_stopped:
                    firewall_down = self.tear_down_firewall()
                    if firewall_down:
                        logger.debug("Firewall down")
                    else:
                        logger.warning("Could not tear firewall down")

                return
            else:
                logger.debug("Process did not die, waiting...")
            tries += 1
            reactor.callLater(self.TERMINATE_WAIT,
                              self._kill_if_left_alive, tries)
            return

        # after running out of patience, we try a killProcess
        logger.debug("Process did not died. Sending a SIGKILL.")
        try:
            self.killit()
        except OSError:
            logger.error("Could not kill process!")

    def killit(self):
        """
        Sends a kill signal to the process.
        """
        self._stop_pollers()
        if self._vpnproc is None:
            logger.debug("There's no vpn process running to kill.")
        else:
            self._vpnproc.aborted = True
            self._vpnproc.killProcess()

    def terminate(self, shutdown=False, restart=False):
        """
        Stops the openvpn subprocess.

        Attempts to send a SIGTERM first, and after a timeout
        it sends a SIGKILL.

        :param shutdown: whether this is the final shutdown
        :type shutdown: bool
        :param restart: whether this stop is part of a hard restart.
        :type restart: bool
        """
        self._stop_pollers()

        # First we try to be polite and send a SIGTERM...
        if self._vpnproc is not None:
            # We assume that the only valid stops are initiated
            # by an user action, not hard restarts
            self._user_stopped = not restart
            self._vpnproc.is_restart = restart

            self._sentterm = True
            self._vpnproc.terminate_openvpn(shutdown=shutdown)

            # ...but we also trigger a countdown to be unpolite
            # if strictly needed.
            reactor.callLater(
                self.TERMINATE_WAIT, self._kill_if_left_alive)

            if IS_LINUX and self._user_stopped:
                firewall_down = self.tear_down_firewall()
                if firewall_down:
                    logger.debug("Firewall down")
                else:
                    logger.warning("Could not tear firewall down")

    def _start_pollers(self):
        """
        Iterate through the registered observers
        and start the looping call for them.
        """
        for poller in self._pollers:
            poller.start(VPNManager.POLL_TIME)

    def _stop_pollers(self):
        """
        Iterate through the registered observers
        and stop the looping calls if they are running.
        """
        for poller in self._pollers:
            if poller.running:
                poller.stop()
        self._pollers = []


class VPNManager(object):
    """
    This is a mixin that we use in the VPNProcess class.
    Here we get together all methods related with the openvpn management
    interface.

    A copy of a QObject containing signals as attributes is passed along
    upon initialization, and we use that object to emit signals to qt-land.

    For more info about management methods::

      zcat `dpkg -L openvpn | grep management`
    """

    # Timers, in secs
    # NOTE: We need to set a bigger poll time in OSX because it seems
    # openvpn malfunctions when you ask it a lot of things in a short
    # amount of time.
    POLL_TIME = 2.5 if IS_MAC else 1.0
    CONNECTION_RETRY_TIME = 1

    def __init__(self, signaler=None):
        """
        Initializes the VPNManager.

        :param signaler: Signaler object used to send notifications to the
                         backend
        :type signaler: backend.Signaler
        """
        self._tn = None
        self._signaler = signaler
        self._aborted = False

    @property
    def aborted(self):
        return self._aborted

    @aborted.setter
    def aborted(self, value):
        self._aborted = value

    def _seek_to_eof(self):
        """
        Read as much as available. Position seek pointer to end of stream
        """
        try:
            self._tn.read_eager()
        except EOFError:
            logger.debug("Could not read from socket. Assuming it died.")
            return

    def _send_command(self, command, until=b"END"):
        """
        Sends a command to the telnet connection and reads until END
        is reached.

        :param command: command to send
        :type command: str

        :param until: byte delimiter string for reading command output
        :type until: byte str

        :return: response read
        :rtype: list
        """
        leap_assert(self._tn, "We need a tn connection!")

        try:
            self._tn.write("%s\n" % (command,))
            buf = self._tn.read_until(until, 2)
            self._seek_to_eof()
            blist = buf.split('\r\n')
            if blist[-1].startswith(until):
                del blist[-1]
                return blist
            else:
                return []

        except socket.error:
            # XXX should get a counter and repeat only
            # after mod X times.
            logger.warning('socket error (command was: "%s")' % (command,))
            self._close_management_socket(announce=False)
            logger.debug('trying to connect to management again')
            self.try_to_connect_to_management(max_retries=5)
            return []

        # XXX should move this to a errBack!
        except Exception as e:
            logger.warning("Error sending command %s: %r" %
                           (command, e))
        return []

    def _close_management_socket(self, announce=True):
        """
        Close connection to openvpn management interface.
        """
        logger.debug('closing socket')
        if announce:
            self._tn.write("quit\n")
            self._tn.read_all()
        self._tn.get_socket().close()
        self._tn = None

    def _connect_management(self, socket_host, socket_port):
        """
        Connects to the management interface on the specified
        socket_host socket_port.

        :param socket_host: either socket path (unix) or socket IP
        :type socket_host: str

        :param socket_port: either string "unix" if it's a unix
                            socket, or port otherwise
        :type socket_port: str
        """
        if self.is_connected():
            self._close_management_socket()

        try:
            self._tn = UDSTelnet(socket_host, socket_port)

            # XXX make password optional
            # specially for win. we should generate
            # the pass on the fly when invoking manager
            # from conductor

            # self.tn.read_until('ENTER PASSWORD:', 2)
            # self.tn.write(self.password + '\n')
            # self.tn.read_until('SUCCESS:', 2)
            if self._tn:
                self._tn.read_eager()

        # XXX move this to the Errback
        except Exception as e:
            logger.warning("Could not connect to OpenVPN yet: %r" % (e,))
            self._tn = None

    def _connectCb(self, *args):
        """
        Callback for connection.

        :param args: not used
        """
        if self._tn:
            logger.info('Connected to management')
        else:
            logger.debug('Cannot connect to management...')

    def _connectErr(self, failure):
        """
        Errorback for connection.

        :param failure: Failure
        """
        logger.warning(failure)

    def connect_to_management(self, host, port):
        """
        Connect to a management interface.

        :param host: the host of the management interface
        :type host: str

        :param port: the port of the management interface
        :type port: str

        :returns: a deferred
        """
        self.connectd = defer.maybeDeferred(
            self._connect_management, host, port)
        self.connectd.addCallbacks(self._connectCb, self._connectErr)
        return self.connectd

    def is_connected(self):
        """
        Returns the status of the management interface.

        :returns: True if connected, False otherwise
        :rtype: bool
        """
        return True if self._tn else False

    def try_to_connect_to_management(self, retry=0, max_retries=None):
        """
        Attempts to connect to a management interface, and retries
        after CONNECTION_RETRY_TIME if not successful.

        :param retry: number of the retry
        :type retry: int
        """
        if max_retries and retry > max_retries:
            logger.warning("Max retries reached while attempting to connect "
                           "to management. Aborting.")
            self.aborted = True
            return

        # _alive flag is set in the VPNProcess class.
        if not self._alive:
            logger.debug('Tried to connect to management but process is '
                         'not alive.')
            return
        logger.debug('trying to connect to management')
        if not self.aborted and not self.is_connected():
            self.connect_to_management(self._socket_host, self._socket_port)
            reactor.callLater(
                self.CONNECTION_RETRY_TIME,
                self.try_to_connect_to_management, retry + 1)

    def _parse_state_and_notify(self, output):
        """
        Parses the output of the state command and emits state_changed
        signal when the state changes.

        :param output: list of lines that the state command printed as
                       its output
        :type output: list
        """
        for line in output:
            stripped = line.strip()
            if stripped == "END":
                continue
            parts = stripped.split(",")
            if len(parts) < 5:
                continue
            ts, status_step, ok, ip, remote = parts

            state = status_step
            if state != self._last_state:
                self._signaler.signal(self._signaler.eip_state_changed, state)
                self._last_state = state

    def _parse_status_and_notify(self, output):
        """
        Parses the output of the status command and emits
        status_changed signal when the status changes.

        :param output: list of lines that the status command printed
                       as its output
        :type output: list
        """
        tun_tap_read = ""
        tun_tap_write = ""

        for line in output:
            stripped = line.strip()
            if stripped.endswith("STATISTICS") or stripped == "END":
                continue
            parts = stripped.split(",")
            if len(parts) < 2:
                continue

            text, value = parts
            # text can be:
            #   "TUN/TAP read bytes"
            #   "TUN/TAP write bytes"
            #   "TCP/UDP read bytes"
            #   "TCP/UDP write bytes"
            #   "Auth read bytes"

            if text == "TUN/TAP read bytes":
                tun_tap_read = value  # download
            elif text == "TUN/TAP write bytes":
                tun_tap_write = value  # upload

        status = (tun_tap_read, tun_tap_write)
        if status != self._last_status:
            self._signaler.signal(self._signaler.eip_status_changed, status)
            self._last_status = status

    def get_state(self):
        """
        Notifies the gui of the output of the state command over
        the openvpn management interface.
        """
        if self.is_connected():
            return self._parse_state_and_notify(self._send_command("state"))

    def get_status(self):
        """
        Notifies the gui of the output of the status command over
        the openvpn management interface.
        """
        if self.is_connected():
            return self._parse_status_and_notify(self._send_command("status"))

    @property
    def vpn_env(self):
        """
        Return a dict containing the vpn environment to be used.
        """
        return self._launcher.get_vpn_env()

    def terminate_openvpn(self, shutdown=False):
        """
        Attempts to terminate openvpn by sending a SIGTERM.
        """
        if self.is_connected():
            self._send_command("signal SIGTERM")
        if shutdown:
            self._cleanup_tempfiles()

    def _cleanup_tempfiles(self):
        """
        Remove all temporal files we might have left behind.

        Iif self.port is 'unix', we have created a temporal socket path that,
        under normal circumstances, we should be able to delete.
        """
        if self._socket_port == "unix":
            logger.debug('cleaning socket file temp folder')
            tempfolder = first(os.path.split(self._socket_host))
            if tempfolder and os.path.isdir(tempfolder):
                try:
                    shutil.rmtree(tempfolder)
                except OSError:
                    logger.error('could not delete tmpfolder %s' % tempfolder)

    def get_openvpn_process(self):
        """
        Looks for openvpn instances running.

        :rtype: process
        """
        openvpn_process = None
        for p in psutil.process_iter():
            try:
                # XXX Not exact!
                # Will give false positives.
                # we should check that cmdline BEGINS
                # with openvpn or with our wrapper
                # (pkexec / osascript / whatever)

                # This needs more work, see #3268, but for the moment
                # we need to be able to filter out arguments in the form
                # --openvpn-foo, since otherwise we are shooting ourselves
                # in the feet.

                if PSUTIL_2:
                    cmdline = p.cmdline()
                else:
                    cmdline = p.cmdline
                if any(map(lambda s: s.find(
                        "LEAPOPENVPN") != -1, cmdline)):
                    openvpn_process = p
                    break
            except psutil_AccessDenied:
                pass
        return openvpn_process

    def stop_if_already_running(self):
        """
        Checks if VPN is already running and tries to stop it.

        Might raise OpenVPNAlreadyRunning.

        :return: True if stopped, False otherwise

        """
        process = self.get_openvpn_process()
        if not process:
            logger.debug('Could not find openvpn process while '
                         'trying to stop it.')
            return

        logger.debug("OpenVPN is already running, trying to stop it...")
        cmdline = process.cmdline

        manag_flag = "--management"
        if isinstance(cmdline, list) and manag_flag in cmdline:
            # we know that our invocation has this distinctive fragment, so
            # we use this fingerprint to tell other invocations apart.
            # this might break if we change the configuration path in the
            # launchers
            smellslikeleap = lambda s: "leap" in s and "providers" in s

            if not any(map(smellslikeleap, cmdline)):
                logger.debug("We cannot stop this instance since we do not "
                             "recognise it as a leap invocation.")
                raise AlienOpenVPNAlreadyRunning

            try:
                index = cmdline.index(manag_flag)
                host = cmdline[index + 1]
                port = cmdline[index + 2]
                logger.debug("Trying to connect to %s:%s"
                             % (host, port))
                self.connect_to_management(host, port)

                # XXX this has a problem with connections to different
                # remotes. So the reconnection will only work when we are
                # terminating instances left running for the same provider.
                # If we are killing an openvpn instance configured for another
                # provider, we will get:
                # TLS Error: local/remote TLS keys are out of sync
                # However, that should be a rare case right now.
                self._send_command("signal SIGTERM")
                self._close_management_socket(announce=True)
            except (Exception, AssertionError) as e:
                logger.warning("Problem trying to terminate OpenVPN: %r"
                               % (e,))
        else:
            logger.debug("Could not find the expected openvpn command line.")

        process = self.get_openvpn_process()
        if process is None:
            logger.debug("Successfully finished already running "
                         "openvpn process.")
            return True
        else:
            logger.warning("Unable to terminate OpenVPN")
            raise OpenVPNAlreadyRunning


class VPNProcess(protocol.ProcessProtocol, VPNManager):
    """
    A ProcessProtocol class that can be used to spawn a process that will
    launch openvpn and connect to its management interface to control it
    programmatically.
    """

    def __init__(self, eipconfig, providerconfig, socket_host, socket_port,
                 signaler, openvpn_verb):
        """
        :param eipconfig: eip configuration object
        :type eipconfig: EIPConfig

        :param providerconfig: provider specific configuration
        :type providerconfig: ProviderConfig

        :param socket_host: either socket path (unix) or socket IP
        :type socket_host: str

        :param socket_port: either string "unix" if it's a unix
                            socket, or port otherwise
        :type socket_port: str

        :param signaler: Signaler object used to receive notifications to the
                         backend
        :type signaler: backend.Signaler

        :param openvpn_verb: the desired level of verbosity in the
                             openvpn invocation
        :type openvpn_verb: int
        """
        VPNManager.__init__(self, signaler=signaler)
        leap_assert_type(eipconfig, EIPConfig)
        leap_assert_type(providerconfig, ProviderConfig)

        # leap_assert(not self.isRunning(), "Starting process more than once!")

        self._eipconfig = eipconfig
        self._providerconfig = providerconfig
        self._socket_host = socket_host
        self._socket_port = socket_port

        self._launcher = get_vpn_launcher()

        self._last_state = None
        self._last_status = None
        self._alive = False

        # XXX use flags, maybe, instead of passing
        # the parameter around.
        self._openvpn_verb = openvpn_verb

        self._vpn_observer = VPNObserver(signaler)
        self.is_restart = False

    # processProtocol methods

    def connectionMade(self):
        """
        Called when the connection is made.

        .. seeAlso: `http://twistedmatrix.com/documents/13.0.0/api/twisted.internet.protocol.ProcessProtocol.html` # noqa
        """
        self._alive = True
        self.aborted = False
        self.try_to_connect_to_management(max_retries=10)

    def outReceived(self, data):
        """
        Called when new data is available on stdout.

        :param data: the data read on stdout

        .. seeAlso: `http://twistedmatrix.com/documents/13.0.0/api/twisted.internet.protocol.ProcessProtocol.html` # noqa
        """
        # truncate the newline
        line = data[:-1]
        vpnlog.info(line)
        self._vpn_observer.watch(line)

    def processExited(self, reason):
        """
        Called when the child process exits.

        .. seeAlso: `http://twistedmatrix.com/documents/13.0.0/api/twisted.internet.protocol.ProcessProtocol.html` # noqa
        """
        exit_code = reason.value.exitCode
        if isinstance(exit_code, int):
            logger.debug("processExited, status %d" % (exit_code,))
        self._signaler.signal(
            self._signaler.eip_process_finished, exit_code)
        self._alive = False

    def processEnded(self, reason):
        """
        Called when the child process exits and all file descriptors associated
        with it have been closed.

        .. seeAlso: `http://twistedmatrix.com/documents/13.0.0/api/twisted.internet.protocol.ProcessProtocol.html` # noqa
        """
        exit_code = reason.value.exitCode
        if isinstance(exit_code, int):
            logger.debug("processEnded, status %d" % (exit_code,))

    # polling

    def pollStatus(self):
        """
        Polls connection status.
        """
        if self._alive:
            self.get_status()

    def pollState(self):
        """
        Polls connection state.
        """
        if self._alive:
            self.get_state()

    # launcher

    def getCommand(self):
        """
        Gets the vpn command from the aproppriate launcher.

        Might throw:
            VPNLauncherException,
            OpenVPNNotFoundException.

        :rtype: list of str
        """
        command = self._launcher.get_vpn_command(
            eipconfig=self._eipconfig,
            providerconfig=self._providerconfig,
            socket_host=self._socket_host,
            socket_port=self._socket_port,
            openvpn_verb=self._openvpn_verb)

        encoding = sys.getfilesystemencoding()
        for i, c in enumerate(command):
            if not isinstance(c, str):
                command[i] = c.encode(encoding)

        logger.debug("Running VPN with command: ")
        logger.debug("{0}".format(" ".join(command)))
        return command

    def getGateways(self):
        """
        Get the gateways from the appropiate launcher.

        :rtype: list
        """
        gateways = self._launcher.get_gateways(
            self._eipconfig, self._providerconfig)
        return gateways

    # shutdown

    def killProcess(self):
        """
        Sends the KILL signal to the running process.
        """
        try:
            self.transport.signalProcess('KILL')
        except internet_error.ProcessExitedAlready:
            logger.debug('Process Exited Already')

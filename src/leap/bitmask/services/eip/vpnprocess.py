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
import logging
import os
import psutil
import psutil.error
import shutil
import socket

from PySide import QtCore

from leap.bitmask.config.providerconfig import ProviderConfig
from leap.bitmask.services.eip import get_vpn_launcher
from leap.bitmask.services.eip.eipconfig import EIPConfig
from leap.bitmask.services.eip.udstelnet import UDSTelnet
from leap.bitmask.util import first
from leap.bitmask.platform_init import IS_MAC
from leap.common.check import leap_assert, leap_assert_type

logger = logging.getLogger(__name__)
vpnlog = logging.getLogger('leap.openvpn')

from twisted.internet import protocol
from twisted.internet import defer
from twisted.internet import error as internet_error
from twisted.internet.task import LoopingCall


class VPNSignals(QtCore.QObject):
    """
    These are the signals that we use to let the UI know
    about the events we are polling.
    They are instantiated in the VPN object and passed along
    till the VPNProcess.
    """
    state_changed = QtCore.Signal(dict)
    status_changed = QtCore.Signal(dict)
    process_finished = QtCore.Signal(int)

    def __init__(self):
        QtCore.QObject.__init__(self)


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
        from twisted.internet import reactor
        self._vpnproc = None
        self._pollers = []
        self._reactor = reactor
        self._qtsigs = VPNSignals()

        # XXX should get it from config.flags
        self._openvpn_verb = kwargs.get(self.OPENVPN_VERB, None)

    @property
    def qtsigs(self):
        return self._qtsigs

    def start(self, *args, **kwargs):
        """
        Starts the openvpn subprocess.

        :param args: args to be passed to the VPNProcess
        :type args: tuple

        :param kwargs: kwargs to be passed to the VPNProcess
        :type kwargs: dict
        """
        self._stop_pollers()
        kwargs['qtsigs'] = self.qtsigs
        kwargs['openvpn_verb'] = self._openvpn_verb

        # start the main vpn subprocess
        vpnproc = VPNProcess(*args, **kwargs)
                             #qtsigs=self.qtsigs,
                             #openvpn_verb=self._openvpn_verb)

        if vpnproc.get_openvpn_process():
            logger.info("Another vpn process is running. Will try to stop it.")
            vpnproc.stop_if_already_running()

        cmd = vpnproc.getCommand()
        env = os.environ
        for key, val in vpnproc.vpn_env.items():
            env[key] = val

        self._reactor.spawnProcess(vpnproc, cmd[0], cmd, env)
        self._vpnproc = vpnproc

        # add pollers for status and state
        # this could be extended to a collection of
        # generic watchers

        poll_list = [LoopingCall(vpnproc.pollStatus),
                     LoopingCall(vpnproc.pollState)]
        self._pollers.extend(poll_list)
        self._start_pollers()

    def _kill_if_left_alive(self, tries=0):
        """
        Check if the process is still alive, and sends a
        SIGKILL after a timeout period.

        :param tries: counter of tries, used in recursion
        :type tries: int
        """
        from twisted.internet import reactor
        while tries < self.TERMINATE_MAXTRIES:
            if self._vpnproc.transport.pid is None:
                logger.debug("Process has been happily terminated.")
                return
            else:
                logger.debug("Process did not die, waiting...")
            tries += 1
            reactor.callLater(self.TERMINATE_WAIT,
                              self._kill_if_left_alive, tries)

        # after running out of patience, we try a killProcess
        logger.debug("Process did not died. Sending a SIGKILL.")
        self.killit()

    def killit(self):
        """
        Sends a kill signal to the process.
        """
        self._stop_pollers()
        self._vpnproc.aborted = True
        self._vpnproc.killProcess()

    def terminate(self, shutdown=False):
        """
        Stops the openvpn subprocess.

        Attempts to send a SIGTERM first, and after a timeout
        it sends a SIGKILL.
        """
        from twisted.internet import reactor
        self._stop_pollers()

        # First we try to be polite and send a SIGTERM...
        if self._vpnproc:
            self._sentterm = True
            self._vpnproc.terminate_openvpn(shutdown=shutdown)

            # ...but we also trigger a countdown to be unpolite
            # if strictly needed.

            # XXX Watch out! This will fail NOW since we are running
            # openvpn as root as a workaround for some connection issues.
            reactor.callLater(
                self.TERMINATE_WAIT, self._kill_if_left_alive)

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

    TS_KEY = "ts"
    STATUS_STEP_KEY = "status_step"
    OK_KEY = "ok"
    IP_KEY = "ip"
    REMOTE_KEY = "remote"

    TUNTAP_READ_KEY = "tun_tap_read"
    TUNTAP_WRITE_KEY = "tun_tap_write"
    TCPUDP_READ_KEY = "tcp_udp_read"
    TCPUDP_WRITE_KEY = "tcp_udp_write"
    AUTH_READ_KEY = "auth_read"

    def __init__(self, qtsigs=None):
        """
        Initializes the VPNManager.

        :param qtsigs: a QObject containing the Qt signals used by the UI
                       to give feedback about state changes.
        :type qtsigs: QObject
        """
        from twisted.internet import reactor
        self._reactor = reactor
        self._tn = None
        self._qtsigs = qtsigs
        self._aborted = False

    @property
    def qtsigs(self):
        return self._qtsigs

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
            self._reactor.callLater(
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

            state_dict = {
                self.TS_KEY: ts,
                self.STATUS_STEP_KEY: status_step,
                self.OK_KEY: ok,
                self.IP_KEY: ip,
                self.REMOTE_KEY: remote
            }

            if state_dict != self._last_state:
                self.qtsigs.state_changed.emit(state_dict)
                self._last_state = state_dict

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
        tcp_udp_read = ""
        tcp_udp_write = ""
        auth_read = ""
        for line in output:
            stripped = line.strip()
            if stripped.endswith("STATISTICS") or stripped == "END":
                continue
            parts = stripped.split(",")
            if len(parts) < 2:
                continue
            if parts[0].strip() == "TUN/TAP read bytes":
                tun_tap_read = parts[1]
            elif parts[0].strip() == "TUN/TAP write bytes":
                tun_tap_write = parts[1]
            elif parts[0].strip() == "TCP/UDP read bytes":
                tcp_udp_read = parts[1]
            elif parts[0].strip() == "TCP/UDP write bytes":
                tcp_udp_write = parts[1]
            elif parts[0].strip() == "Auth read bytes":
                auth_read = parts[1]

        status_dict = {
            self.TUNTAP_READ_KEY: tun_tap_read,
            self.TUNTAP_WRITE_KEY: tun_tap_write,
            self.TCPUDP_READ_KEY: tcp_udp_read,
            self.TCPUDP_WRITE_KEY: tcp_udp_write,
            self.AUTH_READ_KEY: auth_read
        }

        if status_dict != self._last_status:
            self.qtsigs.status_changed.emit(status_dict)
            self._last_status = status_dict

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
                if any(map(lambda s: s.find("LEAPOPENVPN") != -1, p.cmdline)):
                    openvpn_process = p
                    break
            except psutil.error.AccessDenied:
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
            except Exception as e:
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
                 qtsigs, openvpn_verb):
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

        :param qtsigs: a QObject containing the Qt signals used to notify the
                       UI.
        :type qtsigs: QObject

        :param openvpn_verb: the desired level of verbosity in the
                             openvpn invocation
        :type openvpn_verb: int
        """
        VPNManager.__init__(self, qtsigs=qtsigs)
        leap_assert_type(eipconfig, EIPConfig)
        leap_assert_type(providerconfig, ProviderConfig)
        leap_assert_type(qtsigs, QtCore.QObject)

        #leap_assert(not self.isRunning(), "Starting process more than once!")

        self._eipconfig = eipconfig
        self._providerconfig = providerconfig
        self._socket_host = socket_host
        self._socket_port = socket_port

        self._launcher = get_vpn_launcher()

        self._last_state = None
        self._last_status = None
        self._alive = False

        self._openvpn_verb = openvpn_verb

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
        # should send this to the logging window
        vpnlog.info(data[:-1])

    def processExited(self, reason):
        """
        Called when the child process exits.

        .. seeAlso: `http://twistedmatrix.com/documents/13.0.0/api/twisted.internet.protocol.ProcessProtocol.html` # noqa
        """
        exit_code = reason.value.exitCode
        if isinstance(exit_code, int):
            logger.debug("processExited, status %d" % (exit_code,))
        self.qtsigs.process_finished.emit(exit_code)
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

        Might throw: VPNLauncherException, OpenVPNNotFoundException.
        """
        cmd = self._launcher.get_vpn_command(
            eipconfig=self._eipconfig,
            providerconfig=self._providerconfig,
            socket_host=self._socket_host,
            socket_port=self._socket_port,
            openvpn_verb=self._openvpn_verb)
        return map(str, cmd)

    # shutdown

    def killProcess(self):
        """
        Sends the KILL signal to the running process.
        """
        try:
            self.transport.signalProcess('KILL')
        except internet_error.ProcessExitedAlready:
            logger.debug('Process Exited Already')

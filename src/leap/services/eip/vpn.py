# -*- coding: utf-8 -*-
# vpn.py
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
VPN launcher and watcher thread
"""
import logging
import sys

from PySide import QtCore, QtGui
from functools import partial

from leap.config.providerconfig import ProviderConfig
from leap.services.eip.vpnlaunchers import get_platform_launcher
from leap.services.eip.eipconfig import EIPConfig
from leap.services.eip.udstelnet import UDSTelnet
from leap.util.check import leap_assert, leap_assert_type

logger = logging.getLogger(__name__)
ON_POSIX = 'posix' in sys.builtin_module_names


# TODO: abstract the thread that can be asked to quit to another
# generic class that Fetcher and VPN inherit from
class VPN(QtCore.QThread):
    """
    VPN launcher and watcher thread. It will emit signals based on
    different events caught by the management interface
    """

    state_changed = QtCore.Signal(dict)
    status_changed = QtCore.Signal(dict)

    process_finished = QtCore.Signal(int)

    CONNECTION_RETRY_TIME = 1000
    POLL_TIME = 100

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

    def __init__(self):
        QtCore.QThread.__init__(self)

        self._should_quit = False
        self._should_quit_lock = QtCore.QMutex()

        self._launcher = get_platform_launcher()
        self._subp = None

        self._tn = None
        self._host = None
        self._port = None

        self._last_state = None
        self._last_status = None

    def get_should_quit(self):
        """
        Returns wether this thread should quit

        @rtype: bool
        @return: True if the thread should terminate itself, Flase otherwise
        """
        QtCore.QMutexLocker(self._should_quit_lock)
        return self._should_quit

    def set_should_quit(self):
        """
        Sets the should_quit flag to True so that this thread
        terminates the first chance it gets.
        Also terminates the VPN process and the connection to it
        """
        QtCore.QMutexLocker(self._should_quit_lock)
        self._should_quit = True
        if self._tn is None or self._subp is None:
            return

        try:
            self._send_command("signal SIGTERM")
            self._tn.close()
            self._subp.terminate()
        except Exception as e:
            logger.debug("Could not terminate process, trying command " +
                         "signal SIGNINT: %r" % (e,))
        finally:
            self._tn = None

    def start(self, eipconfig, providerconfig, socket_host, socket_port):
        """
        Launches OpenVPN and starts the thread to watch its output

        @param eipconfig: eip configuration object
        @type eipconfig: EIPConfig
        @param providerconfig: provider specific configuration
        @type providerconfig: ProviderConfig
        @param socket_host: either socket path (unix) or socket IP
        @type socket_host: str
        @param socket_port: either string "unix" if it's a unix
        socket, or port otherwise
        @type socket_port: str
        """
        leap_assert(eipconfig, "We need an eip config")
        leap_assert_type(eipconfig, EIPConfig)
        leap_assert(providerconfig, "We need a provider config")
        leap_assert_type(providerconfig, ProviderConfig)
        leap_assert(not self.isRunning(), "Starting process more than once!")

        logger.debug("Starting VPN...")

        with QtCore.QMutexLocker(self._should_quit_lock):
            self._should_quit = False

        command = self._launcher.get_vpn_command(eipconfig=eipconfig,
                                                 providerconfig=providerconfig,
                                                 socket_host=socket_host,
                                                 socket_port=socket_port)
        try:
            self._subp = QtCore.QProcess()
            self._subp.finished.connect(self.process_finished)
            self._subp.start(command[:1][0], command[1:])
            logger.debug("Waiting for started...")
            self._subp.waitForStarted()
            logger.debug("Started!")

            self._host = socket_host
            self._port = socket_port

            self._started = True

            QtCore.QThread.start(self)
        except Exception as e:
            logger.warning("Something went wrong while starting OpenVPN: %r" %
                           (e,))

    def _connect(self, socket_host, socket_port):
        """
        Connects to the specified socket_host socket_port
        @param socket_host: either socket path (unix) or socket IP
        @type socket_host: str
        @param socket_port: either string "unix" if it's a unix
        socket, or port otherwise
        @type socket_port: str
        """
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
        except Exception as e:
            logger.warning("Could not connect to OpenVPN yet: %r" % (e,))
            self._tn = None

    def _disconnect(self):
        """
        Disconnects the telnet connection to the openvpn process
        """
        logger.debug('Closing socket')
        self._tn.write("quit\n")
        self._tn.read_all()
        self._tn.close()
        self._tn = None

    def _send_command(self, command, until=b"END"):
        """
        Sends a command to the telnet connection and reads until END
        is reached

        @param command: command to send
        @type command: str
        @param until: byte delimiter string for reading command output
        @type until: byte str
        @return: response read
        @rtype: list
        """
        leap_assert(self._tn, "We need a tn connection!")
        try:
            self._tn.write("%s\n" % (command,))
            buf = self._tn.read_until(until, 2)
            self._tn.read_eager()
            lines = buf.split("\n")
            return lines
        except Exception as e:
            logger.warning("Error sending command %s: %r" %
                           (command, e))
        return []

    def _parse_state_and_notify(self, output):
        """
        Parses the output of the state command and emits state_changed
        signal when the state changes

        @param output: list of lines that the state command printed as
        its output
        @type output: list
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
                self.state_changed.emit(state_dict)
                self._last_state = state_dict

    def _parse_status_and_notify(self, output):
        """
        Parses the output of the status command and emits
        status_changed signal when the status changes

        @param output: list of lines that the status command printed
        as its output
        @type output: list
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
            self.status_changed.emit(status_dict)
            self._last_status = status_dict

    def run(self):
        """
        Main run loop for this thread
        """
        while True:
            if self.get_should_quit():
                logger.debug("Quitting VPN thread")
                return

            if self._subp and self._subp.state() != QtCore.QProcess.Running:
                QtCore.QThread.msleep(self.CONNECTION_RETRY_TIME)

            if self._tn is None:
                self._connect(self._host, self._port)
                QtCore.QThread.msleep(self.CONNECTION_RETRY_TIME)
            else:
                self._parse_state_and_notify(self._send_command("state"))
                self._parse_status_and_notify(self._send_command("status"))
                output_sofar = self._subp.readAllStandardOutput()
                if len(output_sofar) > 0:
                    logger.debug(output_sofar)
                QtCore.QThread.msleep(self.POLL_TIME)


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    import signal

    def sigint_handler(*args, **kwargs):
        logger.debug('SIGINT catched. shutting down...')
        vpn_thread = args[0]
        vpn_thread.set_should_quit()
        QtGui.QApplication.quit()

    def signal_tester(d):
        print d

    logger = logging.getLogger(name='leap')
    logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s '
        '- %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)

    vpn_thread = VPN()

    sigint = partial(sigint_handler, vpn_thread)
    signal.signal(signal.SIGINT, sigint)

    eipconfig = EIPConfig()
    if eipconfig.load("leap/providers/bitmask.net/eip-service.json"):
        provider = ProviderConfig()
        if provider.load("leap/providers/bitmask.net/provider.json"):
            vpn_thread.start(eipconfig=eipconfig,
                             providerconfig=provider,
                             socket_host="/home/chiiph/vpnsock",
                             socket_port="unix")

    timer = QtCore.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)
    app.connect(app, QtCore.SIGNAL("aboutToQuit()"),
                vpn_thread.set_should_quit)
    w = QtGui.QWidget()
    w.resize(100, 100)
    w.show()

    vpn_thread.state_changed.connect(signal_tester)
    vpn_thread.status_changed.connect(signal_tester)

    sys.exit(app.exec_())

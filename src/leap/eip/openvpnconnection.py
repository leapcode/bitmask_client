"""
OpenVPN Connection
"""
from __future__ import (print_function)
from functools import partial
import logging
import os
import psutil
import shutil
import select
import socket
from time import sleep

logger = logging.getLogger(name=__name__)

from leap.base.connection import Connection
from leap.base.constants import OPENVPN_BIN
from leap.util.coroutines import spawn_and_watch_process
from leap.util.misc import get_openvpn_pids

from leap.eip.udstelnet import UDSTelnet
from leap.eip import config as eip_config
from leap.eip import exceptions as eip_exceptions


class OpenVPNManagement(object):

    # TODO explain a little bit how management interface works
    # and our telnet interface with support for unix sockets.

    """
    for more information, read openvpn management notes.
    zcat `dpkg -L openvpn | grep management`
    """

    def _connect_to_management(self):
        """
        Connect to openvpn management interface
        """
        if hasattr(self, 'tn'):
            self._close_management_socket()
        self.tn = UDSTelnet(self.host, self.port)

        # XXX make password optional
        # specially for win. we should generate
        # the pass on the fly when invoking manager
        # from conductor

        #self.tn.read_until('ENTER PASSWORD:', 2)
        #self.tn.write(self.password + '\n')
        #self.tn.read_until('SUCCESS:', 2)
        if self.tn:
            self._seek_to_eof()
        return True

    def _close_management_socket(self, announce=True):
        """
        Close connection to openvpn management interface
        """
        logger.debug('closing socket')
        if announce:
            self.tn.write("quit\n")
            self.tn.read_all()
        self.tn.get_socket().close()
        del self.tn

    def _seek_to_eof(self):
        """
        Read as much as available. Position seek pointer to end of stream
        """
        try:
            b = self.tn.read_eager()
        except EOFError:
            logger.debug("Could not read from socket. Assuming it died.")
            return
        while b:
            try:
                b = self.tn.read_eager()
            except EOFError:
                logger.debug("Could not read from socket. Assuming it died.")

    def _send_command(self, cmd):
        """
        Send a command to openvpn and return response as list
        """
        if not self.connected():
            try:
                self._connect_to_management()
            except eip_exceptions.MissingSocketError:
                #logger.warning('missing management socket')
                return []
        try:
            if hasattr(self, 'tn'):
                self.tn.write(cmd + "\n")
        except socket.error:
            logger.error('socket error')
            self._close_management_socket(announce=False)
            return []
        try:
            buf = self.tn.read_until(b"END", 2)
            self._seek_to_eof()
            blist = buf.split('\r\n')
            if blist[-1].startswith('END'):
                del blist[-1]
                return blist
            else:
                return []
        except socket.error as exc:
            logger.debug('socket error: %s' % exc.message)
        except select.error as exc:
            logger.debug('select error: %s' % exc.message)

    def _send_short_command(self, cmd):
        """
        parse output from commands that are
        delimited by "success" instead
        """
        if not self.connected():
            self.connect()
        self.tn.write(cmd + "\n")
        # XXX not working?
        buf = self.tn.read_until(b"SUCCESS", 2)
        self._seek_to_eof()
        blist = buf.split('\r\n')
        return blist

    #
    # random maybe useful vpn commands
    #

    def pid(self):
        #XXX broken
        return self._send_short_command("pid")


class OpenVPNConnection(Connection, OpenVPNManagement):
    """
    All related to invocation
    of the openvpn binary.
    It's extended by EIPConnection.
    """

    # XXX Inheriting from Connection was an early design idea
    # but currently that's an empty class.
    # We can get rid of that if we don't use it for sharing
    # state with other leap modules.

    def __init__(self,
                 watcher_cb=None,
                 debug=False,
                 host=None,
                 port="unix",
                 password=None,
                 *args, **kwargs):
        """
        :param watcher_cb: callback to be \
called for each line in watched stdout
        :param signal_map: dictionary of signal names and callables \
to be triggered for each one of them.
        :type watcher_cb: function
        :type signal_map: dict
        """
        #XXX FIXME
        #change watcher_cb to line_observer
        # XXX if not host: raise ImproperlyConfigured

        logger.debug('init openvpn connection')
        self.debug = debug
        self.ovpn_verbosity = kwargs.get('ovpn_verbosity', None)

        self.watcher_cb = watcher_cb
        #self.signal_maps = signal_maps

        self.subp = None
        self.watcher = None

        self.server = None
        self.port = None
        self.proto = None

        self.command = None
        self.args = None

        # XXX get autostart from config
        self.autostart = True

        # management interface init
        self.host = host
        if isinstance(port, str) and port.isdigit():
            port = int(port)
        elif port == "unix":
            port = "unix"
        else:
            port = None
        self.port = port
        self.password = password

    def run_openvpn_checks(self):
        """
        runs check needed before launching
        openvpn subprocess. will raise if errors found.
        """
        logger.debug('running openvpn checks')
        # XXX I think that "check_if_running" should be called
        # from try openvpn connection instead. -- kali.
        # let's prepare tests for that before changing it...
        self._check_if_running_instance()
        self._set_ovpn_command()
        self._check_vpn_keys()

    def try_openvpn_connection(self):
        """
        attempts to connect
        """
        # XXX should make public method
        if self.command is None:
            raise eip_exceptions.EIPNoCommandError
        if self.subp is not None:
            logger.debug('cowardly refusing to launch subprocess again')
            # XXX this is not returning ???!!
            # FIXME -- so it's calling it all the same!!

        self._launch_openvpn()

    def connected(self):
        """
        Returns True if connected
        rtype: bool
        """
        # XXX make a property
        return hasattr(self, 'tn')

    def terminate_openvpn_connection(self, shutdown=False):
        """
        terminates openvpn child subprocess
        """
        if self.subp:
            try:
                self._stop_openvpn()
            except eip_exceptions.ConnectionRefusedError:
                logger.warning(
                    'unable to send sigterm signal to openvpn: '
                    'connection refused.')

            # XXX kali --
            # XXX review-me
            # I think this will block if child process
            # does not return.
            # Maybe we can .poll() for a given
            # interval and exit in any case.

            RETCODE = self.subp.wait()
            if RETCODE:
                logger.error(
                    'cannot terminate subprocess! Retcode %s'
                    '(We might have left openvpn running)' % RETCODE)

        if shutdown:
            self._cleanup_tempfiles()

    def _cleanup_tempfiles(self):
        """
        remove all temporal files
        we might have left behind
        """
        # if self.port is 'unix', we have
        # created a temporal socket path that, under
        # normal circumstances, we should be able to
        # delete

        if self.port == "unix":
            logger.debug('cleaning socket file temp folder')

            tempfolder = os.path.split(self.host)[0]
            if os.path.isdir(tempfolder):
                try:
                    shutil.rmtree(tempfolder)
                except OSError:
                    logger.error('could not delete tmpfolder %s' % tempfolder)

    # checks

    def _check_if_running_instance(self):
        """
        check if openvpn is already running
        """
        openvpn_pids = get_openvpn_pids()
        if openvpn_pids:
            logger.debug('an openvpn instance is already running.')
            logger.debug('attempting to stop openvpn instance.')
            if not self._stop_openvpn():
                raise eip_exceptions.OpenVPNAlreadyRunning
            return
        else:
            logger.debug('no openvpn instance found.')

    def _set_ovpn_command(self):
        try:
            command, args = eip_config.build_ovpn_command(
                provider=self.provider,
                debug=self.debug,
                socket_path=self.host,
                ovpn_verbosity=self.ovpn_verbosity)
        except eip_exceptions.EIPNoPolkitAuthAgentAvailable:
            command = args = None
            raise
        except eip_exceptions.EIPNoPkexecAvailable:
            command = args = None
            raise

        # XXX if not command, signal error.
        self.command = command
        self.args = args

    def _check_vpn_keys(self):
        """
        checks for correct permissions on vpn keys
        """
        try:
            eip_config.check_vpn_keys(provider=self.provider)
        except eip_exceptions.EIPInitBadKeyFilePermError:
            logger.error('Bad VPN Keys permission!')
            # do nothing now
        # and raise the rest ...

    # starting and stopping openvpn subprocess

    def _launch_openvpn(self):
        """
        invocation of openvpn binaries in a subprocess.
        """
        #XXX TODO:
        #deprecate watcher_cb,
        #use _only_ signal_maps instead

        #logger.debug('_launch_openvpn called')
        if self.watcher_cb is not None:
            linewrite_callback = self.watcher_cb
        else:
            #XXX get logger instead
            linewrite_callback = lambda line: logger.debug(
                'watcher: %s' % line)

        # the partial is not
        # being applied now because we're not observing the process
        # stdout like we did in the early stages. but I leave it
        # here since it will be handy for observing patterns in the
        # thru-the-manager updates (with regex)
        observers = (linewrite_callback,
                     partial(lambda con_status,
                             line: linewrite_callback, self.status))
        subp, watcher = spawn_and_watch_process(
            self.command,
            self.args,
            observers=observers)
        self.subp = subp
        self.watcher = watcher

    def _stop_openvpn(self):
        """
        stop openvpn process
        by sending SIGTERM to the management
        interface
        """
        # XXX method a bit too long, split
        logger.debug("atempting to terminate openvpn process...")
        if self.connected():
            try:
                self._send_command("signal SIGTERM\n")
                sleep(1)
                if not self.subp:  # XXX ???
                    return True
            except socket.error:
                logger.warning('management socket died')
                return

        #shutting openvpn failured
        #try patching in old openvpn host and trying again
        # XXX could be more than one!
        process = self._get_openvpn_process()
        if process:
            logger.debug('process: %s' % process.name)
            cmdline = process.cmdline

            manag_flag = "--management"
            if isinstance(cmdline, list) and manag_flag in cmdline:
                _index = cmdline.index(manag_flag)
                self.host = cmdline[_index + 1]
                self._send_command("signal SIGTERM\n")

            #make sure the process was terminated
            process = self._get_openvpn_process()
            if not process:
                logger.debug("Existing OpenVPN Process Terminated")
                return True
            else:
                logger.error("Unable to terminate existing OpenVPN Process.")
                return False

        return True

    def _get_openvpn_process(self):
        for process in psutil.process_iter():
            if OPENVPN_BIN in process.name:
                return process
        return None

    def get_log(self, lines=1):
        log = self._send_command("log %s" % lines)
        return log

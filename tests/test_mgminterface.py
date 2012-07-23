import socket
import select
import telnetlib
import contextlib

from unittest import TestCase

import support

from eip_client.vpnmanager import OpenVPNManager

HOST = "localhost"


class SocketStub(object):
    ''' a socket proxy that re-defines sendall() '''
    def __init__(self, reads=[]):
        self.reads = reads
        self.writes = []
        self.block = False

    def sendall(self, data):
        self.writes.append(data)

    def recv(self, size):
        out = b''
        while self.reads and len(out) < size:
            out += self.reads.pop(0)
            #print(out)
        if len(out) > size:
            self.reads.insert(0, out[size:])
            out = out[:size]
        return out


class TelnetAlike(telnetlib.Telnet):
    def fileno(self):
        raise NotImplementedError()

    def close(self):
        pass

    def sock_avail(self):
        return (not self.sock.block)

    def msg(self, msg, *args):
        with support.captured_stdout() as out:
            telnetlib.Telnet.msg(self, msg, *args)
        self._messages += out.getvalue()
        return

    def read_very_lazy(self):
        self.fill_rawq()
        _all = self.read_all()
        print 'faking lazy:', _all
        return _all


def new_select(*s_args):
    block = False
    for l in s_args:
        for fob in l:
            if isinstance(fob, TelnetAlike):
                block = fob.sock.block
    if block:
        return [[], [], []]
    else:
        return s_args


@contextlib.contextmanager
def test_socket(reads):
    def new_conn(*ignored):
        return SocketStub(reads)
    try:
        old_conn = socket.create_connection
        socket.create_connection = new_conn
        yield None
    finally:
        socket.create_connection = old_conn
    return


#
# VPN Commands Dict
#

vpn_commands = {
        'status': [
            'OpenVPN STATISTICS', 'Updated,Mon Jun 25 11:51:21 2012',
            'TUN/TAP read bytes,306170', 'TUN/TAP write bytes,872102',
            'TCP/UDP read bytes,986177', 'TCP/UDP write bytes,439329',
            'Auth read bytes,872102'],
        'state': ['1340616463,CONNECTED,SUCCESS,172.28.0.2,198.252.153.38'],
        # XXX add more tests
        }


class VPNManagementStub(TelnetAlike):
    epilogue = "\nEND\n"

    def write(self, data):
        #print('data written')
        data = data[:-1]
        if data not in vpn_commands:
            print('not in commands')
            telnetlib.Telnet.write(self, data)
        else:
            msg = '\n'.join(vpn_commands[data]) + self.epilogue
            print 'writing...'
            print msg
            for line in vpn_commands[data]:
                self.sock.reads.append(line)
                #telnetlib.Telnet.write(self, line)
            self.sock.reads.append(self.epilogue)
            #telnetlib.Telnet.write(self, self.epilogue)


def test_telnet(reads=[], cls=VPNManagementStub):
    ''' return a telnetlib.Telnet object that uses a SocketStub with
        reads queued up to be read, and write method mocking a vpn
        management interface'''
    for x in reads:
        assert type(x) is bytes, x
    with test_socket(reads):
        telnet = cls('dummy', 0)
        telnet._messages = ''  # debuglevel output
    return telnet


class ReadTests(TestCase):
    def setUp(self):
        self.old_select = select.select
        select.select = new_select

    def tearDown(self):
        select.select = self.old_select

    def test_read_until(self):
        """
        read_until(expected, timeout=None)
        test the blocking version of read_util
        """
        want = [b'xxxmatchyyy']
        telnet = test_telnet(want)
        data = telnet.read_until(b'match')
        self.assertEqual(data, b'xxxmatch', msg=(telnet.cookedq,
            telnet.rawq, telnet.sock.reads))

        reads = [b'x' * 50, b'match', b'y' * 50]
        expect = b''.join(reads[:-1])
        telnet = test_telnet(reads)
        data = telnet.read_until(b'match')
        self.assertEqual(data, expect)

    def test_read_all(self):
        """
        read_all()
          Read all data until EOF; may block.
        """
        reads = [b'x' * 500, b'y' * 500, b'z' * 500]
        expect = b''.join(reads)
        telnet = test_telnet(reads)
        data = telnet.read_all()
        self.assertEqual(data, expect)
        return

    def test_read_some(self):
        """
        read_some()
          Read at least one byte or EOF; may block.
        """
        # test 'at least one byte'
        telnet = test_telnet([b'x' * 500])
        data = telnet.read_some()
        self.assertTrue(len(data) >= 1)
        # test EOF
        telnet = test_telnet()
        data = telnet.read_some()
        self.assertEqual(b'', data)

    def _read_eager(self, func_name):
        """
        read_*_eager()
          Read all data available already queued or on the socket,
          without blocking.
        """
        want = b'x' * 100
        telnet = test_telnet([want])
        func = getattr(telnet, func_name)
        telnet.sock.block = True
        self.assertEqual(b'', func())
        telnet.sock.block = False
        data = b''
        while True:
            try:
                data += func()
            except EOFError:
                break
        self.assertEqual(data, want)

    def test_read_eager(self):
        # read_eager and read_very_eager make the same gaurantees
        # (they behave differently but we only test the gaurantees)
        self._read_eager('read_eager')
        self._read_eager('read_very_eager')
        #self._read_eager('read_very_lazy')
        # NB -- we need to test the IAC block which is mentioned in the
        # docstring but not in the module docs

    def read_very_lazy(self):
        want = b'x' * 100
        telnet = test_telnet([want])
        self.assertEqual(b'', telnet.read_very_lazy())
        while telnet.sock.reads:
            telnet.fill_rawq()
        data = telnet.read_very_lazy()
        self.assertEqual(want, data)
        self.assertRaises(EOFError, telnet.read_very_lazy)

    def test_read_lazy(self):
        want = b'x' * 100
        telnet = test_telnet([want])
        self.assertEqual(b'', telnet.read_lazy())
        data = b''
        while True:
            try:
                read_data = telnet.read_lazy()
                data += read_data
                if not read_data:
                    telnet.fill_rawq()
            except EOFError:
                break
            self.assertTrue(want.startswith(data))
        self.assertEqual(data, want)


def _seek_to_eof(self):
    """
    Read as much as available. Position seek pointer to end of stream
    """
    #import ipdb;ipdb.set_trace()
    while self.tn.sock.reads:
        print 'reading...'
        print 'and filling rawq'
        self.tn.fill_rawq()
        self.tn.process_rawq()
    try:
        b = self.tn.read_eager()
        while b:
            b = self.tn.read_eager()
    except EOFError:
        pass


def connect_to_stub(self):
    """
    stub to be added to manager
    """
    try:
        self.close()
    except:
        pass
    if self.connected():
        return True
    self.tn = test_telnet()

    self._seek_to_eof()
    return True



class VPNManagerTests(TestCase):

    def setUp(self):
        self.old_select = select.select
        select.select = new_select

        patched_manager = OpenVPNManager
        patched_manager._seek_to_eof = _seek_to_eof
        patched_manager.connect = connect_to_stub
        self.manager = patched_manager()

    def tearDown(self):
        select.select = self.old_select

    # tests

    
    #def test_read_very_lazy(self):
        #want = b'x' * 100
        #telnet = test_telnet()
        #self.assertEqual(b'', telnet.read_very_lazy())
        #print 'writing to telnet'
        #telnet.write('status\n')
        #import ipdb;ipdb.set_trace()
        #while telnet.sock.reads:
            #print 'reading...'
            #print 'and filling rawq'
            #telnet.fill_rawq()
        #import ipdb;ipdb.set_trace()
        #data = telnet.read_very_lazy()
        #print 'data ->', data

    #def test_manager_status(self):
        #buf = self.manager._send_command('state')
        #import ipdb;ipdb.set_trace()
        #print 'buf-->'
        #print buf
#
    def test_manager_state(self):
        buf = self.manager.state()
        print 'buf-->'
        print buf
        import ipdb;ipdb.set_trace()

    def test_command(self):
        commands = [b'status']
        for com in commands:
            telnet = test_telnet()
            telnet.write(com)
            buf = telnet.read_until(b'END')
            print 'buf '
            print buf


def test_main(verbose=None):
    support.run_unittest(
            #ReadTests,
            VPNManagerTests)

if __name__ == '__main__':
    test_main()

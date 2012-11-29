# Copyright 2011 Canonical Ltd.
#
# This file is part of u1db.
#
# u1db is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# u1db is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with u1db.  If not, see <http://www.gnu.org/licenses/>.

import os
import socket
import subprocess
import sys

from u1db import (
    __version__ as _u1db_version,
    open as u1db_open,
    tests,
    )
from u1db.remote import http_client
from u1db.tests.commandline import safe_close


class TestU1DBServe(tests.TestCase):

    def _get_u1db_serve_path(self):
        from u1db import __path__ as u1db_path
        u1db_parent_dir = os.path.dirname(u1db_path[0])
        return os.path.join(u1db_parent_dir, 'u1db-serve')

    def startU1DBServe(self, args):
        command = [sys.executable, self._get_u1db_serve_path()]
        command.extend(args)
        p = subprocess.Popen(command, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(safe_close, p)
        return p

    def test_help(self):
        p = self.startU1DBServe(['--help'])
        stdout, stderr = p.communicate()
        if stderr != '':
            # stderr should normally be empty, but if we are running under
            # python-dbg, it contains the following string
            self.assertRegexpMatches(stderr, r'\[\d+ refs\]')
        self.assertEqual(0, p.returncode)
        self.assertIn('Run the U1DB server', stdout)

    def test_bind_to_port(self):
        p = self.startU1DBServe([])
        starts = 'listening on:'
        x = p.stdout.readline()
        self.assertTrue(x.startswith(starts))
        port = int(x[len(starts):].split(":")[1])
        url = "http://127.0.0.1:%s/" % port
        c = http_client.HTTPClientBase(url)
        self.addCleanup(c.close)
        res, _ = c._request_json('GET', [])
        self.assertEqual({'version': _u1db_version}, res)

    def test_supply_port(self):
        s = socket.socket()
        s.bind(('127.0.0.1', 0))
        host, port = s.getsockname()
        s.close()
        p = self.startU1DBServe(['--port', str(port)])
        x = p.stdout.readline().strip()
        self.assertEqual('listening on: 127.0.0.1:%s' % (port,), x)
        url = "http://127.0.0.1:%s/" % port
        c = http_client.HTTPClientBase(url)
        self.addCleanup(c.close)
        res, _ = c._request_json('GET', [])
        self.assertEqual({'version': _u1db_version}, res)

    def test_bind_to_host(self):
        p = self.startU1DBServe(["--host", "localhost"])
        starts = 'listening on: 127.0.0.1:'
        x = p.stdout.readline()
        self.assertTrue(x.startswith(starts))

    def test_supply_working_dir(self):
        tmp_dir = self.createTempDir('u1db-serve-test')
        db = u1db_open(os.path.join(tmp_dir, 'landmark.db'), create=True)
        db.close()
        p = self.startU1DBServe(['--working-dir', tmp_dir])
        starts = 'listening on:'
        x = p.stdout.readline()
        self.assertTrue(x.startswith(starts))
        port = int(x[len(starts):].split(":")[1])
        url = "http://127.0.0.1:%s/landmark.db" % port
        c = http_client.HTTPClientBase(url)
        self.addCleanup(c.close)
        res, _ = c._request_json('GET', [])
        self.assertEqual({}, res)

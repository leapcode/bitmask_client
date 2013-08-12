## -*- coding: utf-8 -*-
# test_abstrctbootstrapper.py
# Copyright (C) 2013 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


"""
Tests for the Abstract Boostrapper functionality
"""

import mock

from PySide import QtCore

from nose.twistedtools import deferred

from leap.services.abstractbootstrapper import AbstractBootstrapper
from leap.util.pyside_tests_helper import UsesQApplication, BasicPySlotCase


class TesterBootstrapper(AbstractBootstrapper):
    test_signal1 = QtCore.Signal(dict)
    test_signal2 = QtCore.Signal(dict)
    test_signal3 = QtCore.Signal(dict)

    ERROR_MSG = "This is a test error msg"

    def _check_that_passes(self, *args):
        pass

    def _second_check_that_passes(self, *args):
        pass

    def _check_that_fails(self, *args):
        raise Exception(self.ERROR_MSG)

    def run_checks_pass(self):
        cb_chain = [
            (self._check_that_passes, self.test_signal1),
            (self._second_check_that_passes, self.test_signal2),
        ]
        return self.addCallbackChain(cb_chain)

    def run_second_checks_pass(self):
        cb_chain = [
            (self._check_that_passes, None),
        ]
        return self.addCallbackChain(cb_chain)

    def run_checks_fail(self):
        cb_chain = [
            (self._check_that_passes, self.test_signal1),
            (self._check_that_fails, self.test_signal2)
        ]
        return self.addCallbackChain(cb_chain)

    def run_second_checks_fail(self):
        cb_chain = [
            (self._check_that_passes, self.test_signal1),
            (self._check_that_fails, self.test_signal2),
            (self._second_check_that_passes, self.test_signal1)
        ]
        return self.addCallbackChain(cb_chain)

    def run_third_checks_fail(self):
        cb_chain = [
            (self._check_that_passes, self.test_signal1),
            (self._check_that_fails, None)
        ]
        return self.addCallbackChain(cb_chain)


class AbstractBootstrapperTest(UsesQApplication, BasicPySlotCase):
    def setUp(self):
        UsesQApplication.setUp(self)
        BasicPySlotCase.setUp(self)

        self.tbt = TesterBootstrapper()
        self.called1 = self.called2 = 0

    @deferred()
    def test_all_checks_executed_once(self):
        self.tbt._check_that_passes = mock.MagicMock()
        self.tbt._second_check_that_passes = mock.MagicMock()

        d = self.tbt.run_checks_pass()

        def check(*args):
            self.tbt._check_that_passes.assert_called_once_with()
            self.tbt._second_check_that_passes.\
                assert_called_once_with(None)

        d.addCallback(check)
        return d

    #######################################################################
    # Dummy callbacks that test the arguments expected from a certain
    # signal and only allow being called once

    def cb1(self, *args):
        if tuple(self.args1) == args:
            self.called1 += 1
        else:
            raise ValueError('Invalid arguments for callback')

    def cb2(self, *args):
        if tuple(self.args2) == args:
            self.called2 += 1
        else:
            raise ValueError('Invalid arguments for callback')

    #
    #######################################################################

    def _check_cb12_once(self, *args):
        self.assertEquals(self.called1, 1)
        self.assertEquals(self.called2, 1)

    @deferred()
    def test_emits_correct(self):
        self.tbt.test_signal1.connect(self.cb1)
        self.tbt.test_signal2.connect(self.cb2)
        d = self.tbt.run_checks_pass()

        self.args1 = [{
            AbstractBootstrapper.PASSED_KEY: True,
            AbstractBootstrapper.ERROR_KEY: ""
        }]

        self.args2 = self.args1

        d.addCallback(self._check_cb12_once)
        return d

    @deferred()
    def test_emits_failed(self):
        self.tbt.test_signal1.connect(self.cb1)
        self.tbt.test_signal2.connect(self.cb2)
        d = self.tbt.run_checks_fail()

        self.args1 = [{
            AbstractBootstrapper.PASSED_KEY: True,
            AbstractBootstrapper.ERROR_KEY: ""
        }]

        self.args2 = [{
            AbstractBootstrapper.PASSED_KEY: False,
            AbstractBootstrapper.ERROR_KEY:
            TesterBootstrapper.ERROR_MSG
        }]

        d.addCallback(self._check_cb12_once)
        return d

    @deferred()
    def test_emits_failed_and_stops(self):
        self.tbt.test_signal1.connect(self.cb1)
        self.tbt.test_signal2.connect(self.cb2)
        self.tbt.test_signal3.connect(self.cb1)
        d = self.tbt.run_second_checks_fail()

        self.args1 = [{
            AbstractBootstrapper.PASSED_KEY: True,
            AbstractBootstrapper.ERROR_KEY: ""
        }]

        self.args2 = [{
            AbstractBootstrapper.PASSED_KEY: False,
            AbstractBootstrapper.ERROR_KEY:
            TesterBootstrapper.ERROR_MSG
        }]

        d.addCallback(self._check_cb12_once)
        return d

    @deferred()
    def test_failed_without_signal(self):
        d = self.tbt.run_third_checks_fail()
        return d

    @deferred()
    def test_sucess_without_signal(self):
        d = self.tbt.run_second_checks_pass()
        return d

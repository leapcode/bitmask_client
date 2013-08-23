# -*- coding: utf-8 -*-
# password.py
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
Password utilities
"""
from PySide import QtCore

WEAK_PASSWORDS = ("123456", "qweasd", "qwerty", "password")


def basic_password_checks(username, password, password2):
    """
    Performs basic password checks to avoid really easy passwords.

    :param username: username provided at the registrarion form
    :type username: str
    :param password: password from the registration form
    :type password: str
    :param password2: second password from the registration form
    :type password: str

    :returns: True and empty message if all the checks pass,
              False and an error message otherwise
    :rtype: tuple(bool, str)
    """
    # translation helper
    _tr = QtCore.QObject().tr

    message = None

    if message is None and password != password2:
        message = _tr("Passwords don't match")

    if message is None and len(password) < 6:
        message = _tr("Password too short")

    if message is None and password in WEAK_PASSWORDS:
        message = _tr("Password too easy")

    if message is None and username == password:
        message = _tr("Password equal to username")

    return message is None, message

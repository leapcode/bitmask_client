# -*- coding: utf-8 -*-
# repair.py
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
Utils for repairing mailbox indexes.
"""
import logging
import getpass
import os

from collections import defaultdict

from leap.bitmask.config.providerconfig import ProviderConfig
from leap.bitmask.crypto.srpauth import SRPAuth
from leap.bitmask.util import get_path_prefix
from leap.bitmask.services.soledad.soledadbootstrapper import get_db_paths

from leap.mail.imap.account import SoledadBackedAccount
from leap.soledad.client import Soledad

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def initialize_soledad(uuid, email, passwd,
                       secrets, localdb,
                       gnupg_home, tempdir):
    """
    Initializes soledad by hand

    :param email: ID for the user
    :param gnupg_home: path to home used by gnupg
    :param tempdir: path to temporal dir
    :rtype: Soledad instance
    """
    # XXX TODO unify with an authoritative source of mocks
    # for soledad (or partial initializations).
    # This is copied from the imap tests.

    server_url = "http://provider"
    cert_file = ""

    class Mock(object):
        def __init__(self, return_value=None):
            self._return = return_value

        def __call__(self, *args, **kwargs):
            return self._return

    class MockSharedDB(object):

        get_doc = Mock()
        put_doc = Mock()
        lock = Mock(return_value=('atoken', 300))
        unlock = Mock(return_value=True)

        def __call__(self):
            return self

    Soledad._shared_db = MockSharedDB()
    soledad = Soledad(
        uuid,
        passwd,
        secrets,
        localdb,
        server_url,
        cert_file)

    return soledad


class MBOXPlumber(object):
    """
    An class that can fix things inside a soledadbacked account.
    The idea is to gather in this helper different fixes for mailboxes
    that can be invoked when data migration in the client is needed.
    """

    def __init__(self, userid, passwd):
        """
        Initializes the plumber with all that's needed to authenticate
        against the provider.

        :param userid: user identifier, foo@bar
        :type userid: basestring
        :param passwd: the soledad passphrase
        :type passwd: basestring
        """
        self.userid = userid
        self.passwd = passwd
        user, provider = userid.split('@')
        self.user = user
        self.sol = None
        provider_config_path = os.path.join(
            get_path_prefix(),
            "leap", "providers",
            provider, "provider.json")
        provider_config = ProviderConfig()
        loaded = provider_config.load(provider_config_path)
        if not loaded:
            print "could not load provider config!"
            return self.exit()

        self.srp = SRPAuth(provider_config)
        self.srp.authentication_finished.connect(self.repair_account)

    def start_auth(self):
        """
        returns the user identifier for a given provider.

        :param provider: the provider to which we authenticate against.
        """
        print "Authenticating with provider..."
        self.d = self.srp.authenticate(self.user, self.passwd)

    def repair_account(self, *args):
        """
        Gets the user id for this account.
        """
        print "Got authenticated."
        self.uid = self.srp.get_uid()
        if not self.uid:
            print "Got BAD UID from provider!"
            return self.exit()
        print "UID: %s" % (self.uid)

        secrets, localdb = get_db_paths(self.uid)

        self.sol = initialize_soledad(
            self.uid, self.userid, self.passwd,
            secrets, localdb, "/tmp", "/tmp")

        self.acct = SoledadBackedAccount(self.userid, self.sol)
        for mbox_name in self.acct.mailboxes:
            self.repair_mbox_uids(mbox_name)
        print "done."
        self.exit()

    def repair_mbox_uids(self, mbox_name):
        """
        Repairs indexes for a given mbox

        :param mbox_name: mailbox to repair
        :type mbox_name: basestring
        """
        print
        print "REPAIRING INDEXES FOR MAILBOX %s" % (mbox_name,)
        print "----------------------------------------------"
        mbox = self.acct.getMailbox(mbox_name)
        len_mbox = mbox.getMessageCount()
        print "There are %s messages" % (len_mbox,)

        last_ok = True if mbox.last_uid == len_mbox else False
        uids_iter = (doc.content['uid'] for doc in mbox.messages.get_all())
        dupes = self._has_dupes(uids_iter)
        if last_ok and not dupes:
            print "Mbox does not need repair."
            return

        msgs = mbox.messages.get_all()
        for zindex, doc in enumerate(msgs):
            mindex = zindex + 1
            old_uid = doc.content['uid']
            doc.content['uid'] = mindex
            self.sol.put_doc(doc)
            if mindex != old_uid:
                print "%s -> %s (%s)" % (mindex, doc.content['uid'], old_uid)

        old_last_uid = mbox.last_uid
        mbox.last_uid = len_mbox
        print "LAST UID: %s (%s)" % (mbox.last_uid, old_last_uid)

    def _has_dupes(self, sequence):
        """
        Returns True if the given sequence of ints has duplicates.

        :param sequence: a sequence of ints
        :type sequence: sequence
        :rtype: bool
        """
        d = defaultdict(lambda: 0)
        for uid in sequence:
            d[uid] += 1
            if d[uid] != 1:
                return True
        return False

    def exit(self):
        from twisted.internet import reactor
        self.d.cancel()
        if self.sol:
            self.sol.close()
        try:
            reactor.stop()
        except Exception:
            pass
        return


def repair_account(userid):
    """
    Starts repair process for a given account.
    :param userid: the user id (email-like)
    """
    from twisted.internet import reactor
    passwd = unicode(getpass.getpass("Passphrase: "))

    # go mario!
    plumber = MBOXPlumber(userid, passwd)
    reactor.callLater(1, plumber.start_auth)
    reactor.run()


if __name__ == "__main__":
    import sys

    logging.basicConfig()

    if len(sys.argv) != 2:
        print "Usage: repair <username>"
        sys.exit(1)
    repair_account(sys.argv[1])

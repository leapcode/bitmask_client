import os
import gnupg
import re

class GPGWrapper(gnupg.GPG):
    """
    This is a temporary class for handling GPG requests, and should be
    replaced by a more general class used throughout the project.
    """

    GNUPG_HOME    = os.environ['HOME'] + "/.config/leap/gnupg"
    GNUPG_BINARY  = "/usr/bin/gpg" # this has to be changed based on OS

    def __init__(self, gpghome=GNUPG_HOME, gpgbinary=GNUPG_BINARY):
        super(GPGWrapper, self).__init__(gnupghome=gpghome, gpgbinary=gpgbinary)

    def find_key(self, email):
        """
        Find user's key based on their email.
        """
        for key in self.list_keys():
            for uid in key['uids']:
                if re.search(email, uid):
                    return key
        raise LookupError("GnuPG public key for %s not found!" % email)

    def encrypt(self, data, recipient, sign=None, always_trust=True,
                passphrase=None, symmetric=False):
        # TODO: devise a way so we don't need to "always trust".
        return super(GPGWrapper, self).encrypt(data, recipient, sign=sign,
                                               always_trust=always_trust,
                                               passphrase=passphrase,
                                               symmetric=symmetric)

    def decrypt(self, data, always_trust=True, passphrase=None):
        # TODO: devise a way so we don't need to "always trust".
        return super(GPGWrapper, self).decrypt(data,
                                               always_trust=always_trust,
                                               passphrase=passphrase)

    def send_keys(self, keyserver, *keyids):
        """
        Send keys to a keyserver
        """
        result = self.result_map['list'](self)
        logger.debug('send_keys: %r', keyids)
        data = _make_binary_stream("", self.encoding)
        args = ['--keyserver', keyserver, '--send-keys']
        args.extend(keyids)
        self._handle_io(args, data, result, binary=True)
        logger.debug('send_keys result: %r', result.__dict__)
        data.close()
        return result


#----------------------------------------------------------------------------
# u1db Transaction and Sync logs.
#----------------------------------------------------------------------------

class SimpleLog(object):
    def __init__(self):
        self._log = []

    def _set_log(self, log):
        self._log = log

    def _get_log(self):
        return self._log

    log = property(
        _get_log, _set_log, doc="Log contents.")

    def append(self, msg):
        self._log.append(msg)

    def reduce(self, func, initializer=None):
        return reduce(func, self.log, initializer)

    def map(self, func):
        return map(func, self.log)

    def filter(self, func):
        return filter(func, self.log)


class TransactionLog(SimpleLog):
    """
    An ordered list of (generation, doc_id, transaction_id) tuples.
    """

    def _set_log(self, log):
        self._log = log

    def _get_log(self):
        return sorted(self._log, reverse=True)

    log = property(
        _get_log, _set_log, doc="Log contents.")

    def get_generation(self):
        """
        Return the current generation.
        """
        gens = self.map(lambda x: x[0])
        if not gens:
            return 0
        return max(gens)

    def get_generation_info(self):
        """
        Return the current generation and transaction id.
        """
        if not self._log:
            return(0, '')
        info = self.map(lambda x: (x[0], x[2]))
        return reduce(lambda x, y: x if (x[0] > y[0]) else y, info)

    def get_trans_id_for_gen(self, gen):
        """
        Get the transaction id corresponding to a particular generation.
        """
        log = self.reduce(lambda x, y: y if y[0] == gen else x)
        if log is None:
            return None
        return log[2]

    def whats_changed(self, old_generation):
        """
        Return a list of documents that have changed since old_generation.
        """
        results = self.filter(lambda x: x[0] > old_generation)
        seen = set()
        changes = []
        newest_trans_id = ''
        for generation, doc_id, trans_id in results:
            if doc_id not in seen:
                changes.append((doc_id, generation, trans_id))
                seen.add(doc_id)
        if changes:
            cur_gen = changes[0][1]  # max generation
            newest_trans_id = changes[0][2]
            changes.reverse()
        else:
            results = self.log
            if not results:
                cur_gen = 0
                newest_trans_id = ''
            else:
                cur_gen, _, newest_trans_id = results[0]

        return cur_gen, newest_trans_id, changes
        


class SyncLog(SimpleLog):
    """
    A list of (replica_id, generation, transaction_id) tuples.
    """

    def find_by_replica_uid(self, replica_uid):
        if not self.log:
            return ()
        return self.reduce(lambda x, y: y if y[0] == replica_uid else x)

    def get_replica_gen_and_trans_id(self, other_replica_uid):
        """
        Return the last known generation and transaction id for the other db
        replica.
        """
        info = self.find_by_replica_uid(other_replica_uid)
        if not info:
            return (0, '')
        return (info[1], info[2])

    def set_replica_gen_and_trans_id(self, other_replica_uid,
                                      other_generation, other_transaction_id):
        """
        Set the last-known generation and transaction id for the other
        database replica.
        """
        self.log = self.filter(lambda x: x[0] != other_replica_uid)
        self.append((other_replica_uid, other_generation,
                     other_transaction_id))


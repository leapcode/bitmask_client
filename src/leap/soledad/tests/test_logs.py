import unittest2 as unittest
from leap.soledad.backends.objectstore import TransactionLog, SyncLog, ConflictLog


class LogTestCase(unittest.TestCase):

    def test_transaction_log(self):
        data = [
          (2, "doc_3", "tran_3"),
          (3, "doc_2", "tran_2"),
          (1, "doc_1", "tran_1")
        ]
        log = TransactionLog()
        log.log = data
        self.assertEqual(log.get_generation(), 3, 'error getting generation')
        self.assertEqual(log.get_generation_info(), (3, 'tran_2'),
                         'error getting generation info')
        self.assertEqual(log.get_trans_id_for_gen(1), 'tran_1',
                         'error getting trans_id for gen')
        self.assertEqual(log.get_trans_id_for_gen(2), 'tran_3',
                         'error getting trans_id for gen')
        self.assertEqual(log.get_trans_id_for_gen(3), 'tran_2',
                         'error getting trans_id for gen')

    def test_sync_log(self):
        data = [
          ("replica_3", 3, "tran_3"),
          ("replica_2", 2, "tran_2"),
          ("replica_1", 1, "tran_1")
        ]
        log = SyncLog()
        log.log = data
        # test getting
        self.assertEqual(log.get_replica_gen_and_trans_id('replica_3'),
            (3, 'tran_3'), 'error getting replica gen and trans id')
        self.assertEqual(log.get_replica_gen_and_trans_id('replica_2'),
            (2, 'tran_2'), 'error getting replica gen and trans id')
        self.assertEqual(log.get_replica_gen_and_trans_id('replica_1'),
            (1, 'tran_1'), 'error getting replica gen and trans id')
        # test setting
        log.set_replica_gen_and_trans_id('replica_1', 2, 'tran_12')
        self.assertEqual(len(log._log), 3, 'error in log size after setting')
        self.assertEqual(log.get_replica_gen_and_trans_id('replica_1'),
            (2, 'tran_12'), 'error setting replica gen and trans id')
        self.assertEqual(log.get_replica_gen_and_trans_id('replica_2'),
            (2, 'tran_2'), 'error setting replica gen and trans id')
        self.assertEqual(log.get_replica_gen_and_trans_id('replica_3'),
            (3, 'tran_3'), 'error setting replica gen and trans id')

    def test_whats_changed(self):
        data = [
            (1, "doc_1", "tran_1"),
            (2, "doc_2", "tran_2"),
            (3, "doc_3", "tran_3")
          ]
        log = TransactionLog()
        log.log = data
        self.assertEqual(
          log.whats_changed(3),
          (3, "tran_3", []),
          'error getting whats changed.')
        self.assertEqual(
          log.whats_changed(2),
          (3, "tran_3", [("doc_3",3,"tran_3")]),
          'error getting whats changed.')
        self.assertEqual(
          log.whats_changed(1),
          (3, "tran_3", [("doc_2",2,"tran_2"),("doc_3",3,"tran_3")]),
          'error getting whats changed.')

    def test_conflict_log(self):
        # TODO: include tests for `get_conflicts` and `has_conflicts`.
        data = [('1', 'my:1', 'irrelevant'),
                ('2', 'my:1', 'irrelevant'),
                ('3', 'my:1', 'irrelevant')]
        log = ConflictLog(None)
        log.log = data
        log.delete_conflicts([('1','my:1'),('2','my:1')])
        self.assertEqual(
          log.log,
          [('3', 'my:1', 'irrelevant')],
          'error deleting conflicts.')


if __name__ == '__main__':
    unittest.main()


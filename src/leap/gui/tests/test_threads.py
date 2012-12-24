import unittest

import mock
from leap.gui import threads


class FunThreadTestCase(unittest.TestCase):

    def setUp(self):
        self.fun = mock.MagicMock()
        self.fun.return_value = "foo"
        self.t = threads.FunThread(fun=self.fun)

    def test_thread(self):
        self.t.begin()
        self.t.wait()
        self.fun.assert_called()
        del self.t

    def test_run(self):
        # this is called by PyQt
        self.t.run()
        del self.t
        self.fun.assert_called()

if __name__ == "__main__":
    unittest.main()

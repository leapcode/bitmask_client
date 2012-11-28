import sys
import unittest

import tests

def test_suite():
    return tests.test_suite()

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
